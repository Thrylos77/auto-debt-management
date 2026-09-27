"""sales/tests/test_views.py"""
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from sales.models import CreditSale, CreditSaleStatus
from crm.models import Portfolio
from rbac.models import Permission, Role, RoleAssignment
from receivables.models import Debt, TermStatus

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestCreditSaleViews:
    def test_list_sales(self, api_client, new_user, new_customer):
        """Test listing credit sales."""
        # Create a sale manually first
        portfolio = Portfolio.objects.create(ref='PF_TEST_VIEW', commercial=new_user)
        CreditSale.objects.create(
            customer=new_customer,
            commercial=new_user,
            portfolio=portfolio,
            total_amount=Decimal('1000.00')
        )
        
        url = reverse('creditsale-list')
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_create_sale(self, api_client, new_user, new_customer):
        """Test creating a credit sale via API."""
        # Ensure the user has a portfolio or the system assigns one
        Portfolio.objects.create(ref='PF_DEFAULT', commercial=new_user)
        
        url = reverse('creditsale-list')
        api_client.force_authenticate(user=new_user)
        data = {
            'customer': new_customer.pk,
            'total_amount': '5000.00',
            'deposit': '500.00'
        }
        response = api_client.post(url, data)
        assert response.status_code == 201
@pytest.mark.django_db
class TestCreditSalePermissionGuards:
    """Validates permission-based guards on custom actions (fail-closed + SoD)."""

    @staticmethod
    def _user_with_permissions(*codes):
        """Creates an active non-superuser holding the given permission codes."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username='perm_{}'.format(abs(hash(codes)) % (10 ** 8)),
            email='perm_{}@example.com'.format(abs(hash(codes)) % (10 ** 8)),
            password='pw',
            is_active=True,
        )
        role, _ = Role.objects.get_or_create(
            name='ROLE_{}'.format(abs(hash(codes)) % (10 ** 8))
        )
        for code in codes:
            perm, _ = Permission.objects.get_or_create(code=code, label=code)
            role.permissions.add(perm)
        RoleAssignment.objects.create(user=user, role=role)
        return user

    @staticmethod
    def _make_sale(commercial, customer):
        portfolio = Portfolio.objects.create(ref='PF_GUARD', commercial=commercial)
        return CreditSale.objects.create(
            customer=customer,
            commercial=commercial,
            portfolio=portfolio,
            total_amount=Decimal('1000.00'),
        )

    def test_change_status_forbidden_for_authenticated_user_without_permission(
        self, api_client, new_customer
    ):
        """A commercial (even with creditsale.create) cannot change status without
        the dedicated `creditsale.change_status` permission."""
        commercial = self._user_with_permissions('creditsale.create')
        sale = self._make_sale(commercial, new_customer)
        api_client.force_authenticate(user=commercial)
        url = reverse('creditsale-change-status', kwargs={'pk': sale.pk})
        response = api_client.post(url, {'status': 'approved'}, format='json')
        assert response.status_code == 403
        sale.refresh_from_db()
        assert sale.status == CreditSaleStatus.PENDING_APPROVAL

    def test_change_status_allowed_for_user_with_permission(self, api_client, new_customer):
        """An approver holding `creditsale.change_status` (+ list_all scope) can
        approve a sale, which automatically creates the associated Debt."""
        approver = self._user_with_permissions(
            'creditsale.change_status', 'creditsale.list_all'
        )
        commercial = self._user_with_permissions('creditsale.create')
        sale = self._make_sale(commercial, new_customer)
        api_client.force_authenticate(user=approver)
        url = reverse('creditsale-change-status', kwargs={'pk': sale.pk})
        response = api_client.post(url, {'status': 'approved'}, format='json')
        assert response.status_code == 200
        sale.refresh_from_db()
        assert sale.status == CreditSaleStatus.APPROVED
        debt = Debt.objects.get(sale=sale)
        # Default month_duration (1) generates a single full-amount term
        assert debt.month_duration == 1
        assert debt.monthly_payment == Decimal('1000.00')
        terms = list(debt.terms.all())
        assert len(terms) == 1
        assert terms[0].except_amount == Decimal('1000.00')
        assert terms[0].term_status == TermStatus.UNPAID

    def test_approval_generates_terms_from_sale_month_duration(self, api_client, new_customer):
        """Approving a sale reports month_duration onto the Debt and generates
        as many Terms as sale.month_duration, splitting the amount evenly."""
        approver = self._user_with_permissions(
            'creditsale.change_status', 'creditsale.list_all'
        )
        commercial = self._user_with_permissions('creditsale.create')
        portfolio = Portfolio.objects.create(ref='PF_TERMS', commercial=commercial)
        sale = CreditSale.objects.create(
            customer=new_customer,
            commercial=commercial,
            portfolio=portfolio,
            total_amount=Decimal('1200.00'),
            deposit=Decimal('200.00'),
            month_duration=6,
        )
        api_client.force_authenticate(user=approver)
        url = reverse('creditsale-change-status', kwargs={'pk': sale.pk})
        response = api_client.post(url, {'status': 'approved'}, format='json')
        assert response.status_code == 200
        sale.refresh_from_db()
        assert sale.status == CreditSaleStatus.APPROVED

        debt = Debt.objects.get(sale=sale)
        assert debt.month_duration == 6
        assert debt.init_amount == Decimal('1000.00')
        assert debt.monthly_payment == Decimal('166.67')

        terms = list(debt.terms.all().order_by('term_date'))
        assert len(terms) == 6
        assert [t.except_amount for t in terms] == [Decimal('166.67')] * 5 + [Decimal('166.65')]
        assert sum((t.except_amount for t in terms), Decimal('0.00')) == debt.init_amount
        assert all(t.term_status == TermStatus.UNPAID for t in terms)

    def test_commercial_cannot_approve_own_sale_even_with_permission(
        self, api_client, new_customer
    ):
        """Segregation of duties: the commercial who owns the sale cannot approve
        or reject it, even if they hold `creditsale.change_status`."""
        commercial = self._user_with_permissions(
            'creditsale.create', 'creditsale.list_all', 'creditsale.change_status'
        )
        sale = self._make_sale(commercial, new_customer)
        api_client.force_authenticate(user=commercial)
        url = reverse('creditsale-change-status', kwargs={'pk': sale.pk})
        response = api_client.post(url, {'status': 'approved'}, format='json')
        assert response.status_code == 403
        sale.refresh_from_db()
        assert sale.status == CreditSaleStatus.PENDING_APPROVAL

    def test_change_status_forbidden_without_authentication(self, api_client, new_customer):
        commercial = self._user_with_permissions('creditsale.create')
        sale = self._make_sale(commercial, new_customer)
        url = reverse('creditsale-change-status', kwargs={'pk': sale.pk})
        response = api_client.post(url, {'status': 'approved'}, format='json')
        assert response.status_code in (401, 403)

    def test_list_all_requires_permission(self, api_client, new_customer):
        commercial = self._user_with_permissions('creditsale.create')
        api_client.force_authenticate(user=commercial)
        url = reverse('creditsale-list-all')
        response = api_client.get(url)
        assert response.status_code == 403

        consultant = self._user_with_permissions('creditsale.list_all')
        # Create a sale first so the filtered list is non-empty.
        self._make_sale(consultant, new_customer)
        api_client.force_authenticate(user=consultant)
        response = api_client.get(url)
        assert response.status_code == 200
        assert CreditSale.objects.count() >= 1