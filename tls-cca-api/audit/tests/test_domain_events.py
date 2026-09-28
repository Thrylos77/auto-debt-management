"""Regression tests for business-domain audit events."""

from decimal import Decimal

import pytest
from django.utils import timezone

from audit.models import AuditEvent
from crm.models import Portfolio
from crm.services.portfolio_services import create_portfolio_for_commercial
from receivables.models import Debt, Term
from receivables.services.recovery_services import create_recovery
from sales.models import CreditSale
from sales.services.creditsale_services import update_credit_sale_status
from sales.models import CreditSaleStatus


@pytest.mark.django_db
class TestDomainAuditEvents:
    def test_portfolio_creation_is_audited(self):
        from users.models import User

        user = User.objects.create_user(
            username="portfolio-audit",
            email="portfolio-audit@example.com",
            password="x",
            is_active=True,
        )
        portfolio = create_portfolio_for_commercial(user)

        event = AuditEvent.objects.filter(
            action="portfolio.create",
            resource_id=str(portfolio.pk),
        ).first()

        assert event is not None
        assert event.status == "success"
        assert event.actor_user_id == user.pk

    def test_credit_sale_status_change_is_audited(self, new_user, new_customer):
        portfolio = Portfolio.objects.create(
            ref="PF_AUDIT_SALE",
            commercial=new_user,
        )
        sale = CreditSale.objects.create(
            customer=new_customer,
            commercial=new_user,
            portfolio=portfolio,
            total_amount=Decimal("1000.00"),
        )

        update_credit_sale_status(
            sale,
            CreditSaleStatus.CANCELLED,
            user=new_user,
        )

        event = AuditEvent.objects.filter(
            action="creditsale.status_change",
            resource_id=str(sale.pk),
        ).first()

        assert event is not None
        assert event.metadata["previous_status"] == CreditSaleStatus.PENDING_APPROVAL
        assert event.metadata["new_status"] == CreditSaleStatus.CANCELLED

    def test_recovery_creation_is_audited(self, new_user, new_customer):
        portfolio = Portfolio.objects.create(
            ref="PF_AUDIT_RECOVERY",
            commercial=new_user,
        )
        sale = CreditSale.objects.create(
            customer=new_customer,
            commercial=new_user,
            portfolio=portfolio,
            total_amount=Decimal("500.00"),
        )
        debt = Debt.objects.create(
            sale=sale,
            init_amount=Decimal("500.00"),
            balance=Decimal("500.00"),
        )
        term = Term.objects.create(
            debt=debt,
            term_date=timezone.localdate(),
            except_amount=Decimal("500.00"),
            pay_amount=Decimal("0.00"),
        )

        recovery = create_recovery(
            commercial=new_user,
            term=term,
            amount=Decimal("100.00"),
            payment_mode="cash",
        )

        event = AuditEvent.objects.filter(
            action="recovery.create",
            resource_id=str(recovery.pk),
        ).first()

        assert event is not None
        assert event.metadata["term_id"] == term.pk
        assert event.metadata["debt_id"] == debt.pk
        assert event.metadata["amount"] == "100.00"

        debt.refresh_from_db()
        assert debt.balance == Decimal("400.00")

