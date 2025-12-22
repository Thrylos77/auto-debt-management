# crm/services/customer_services.py
from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta
from django.db.models import Max, Q, Subquery, OuterRef

from ..models import Customer, PhysicalPersonDetail, MoralPersonDetail, Portfolio
from sales.models import CreditSale
from receivables.models import Debt


def create_customer(validated_data: dict, creator=None) -> Customer:
    """
    Creates a Customer with its corresponding physical or moral details.
    Runs within a transaction to ensure data integrity.
    Automatically assigns the customer to the creator's active portfolio.
    """
    with transaction.atomic():
        physical_detail_data = validated_data.pop('physical_detail', None)
        moral_detail_data = validated_data.pop('moral_detail', None)

        # Automatically assign portfolio from the creator (commercial) if not provided
        if creator and not validated_data.get('portfolio'):
            portfolio = Portfolio.objects.filter(commercial=creator, active=True).first()
            if portfolio:
                validated_data['portfolio'] = portfolio
        
        customer = Customer.objects.create(**validated_data)
        
        if customer.customer_type == Customer.TYPE_PHYSICAL and physical_detail_data:
            PhysicalPersonDetail.objects.create(customer=customer, **physical_detail_data)
        elif customer.customer_type == Customer.TYPE_MORAL and moral_detail_data:
            MoralPersonDetail.objects.create(customer=customer, **moral_detail_data)
                
        return customer


@transaction.atomic
def update_customer(instance: Customer, validated_data: dict) -> Customer:
    """
    Updates a Customer and its nested details.
    Handles the complexity of switching customer_type.
    """
    # Note: This is a basic implementation. A real-world scenario might need
    # to handle switching customer_type (e.g., deleting the old detail record
    # and creating a new one). For now, we focus on updating existing data.

    physical_detail_data = validated_data.pop('physical_detail', None)
    moral_detail_data = validated_data.pop('moral_detail', None)

    # Update Customer fields
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()

    # Update nested details
    if instance.customer_type == Customer.TYPE_PHYSICAL and physical_detail_data:
        PhysicalPersonDetail.objects.update_or_create(customer=instance, defaults=physical_detail_data)
    elif instance.customer_type == Customer.TYPE_MORAL and moral_detail_data:
        MoralPersonDetail.objects.update_or_create(customer=instance, defaults=moral_detail_data)

    return instance


def activate_customer(customer: Customer) -> Customer:
    """ Set customer as active """
    if not customer.is_active:
        customer.is_active = True
        customer.save(update_fields=['is_active'])
    return customer

def deactivate_customer(customer: Customer) -> Customer:
    """ Set customer as inactive """
    if customer.is_active:
        customer.is_active = False
        customer.save(update_fields=['is_active'])
    return customer

def auto_deactivate_inactive_customers() -> tuple[int, int]:
    """
    Deactivates customers who have been inactive for more than 4 years.

    An active customer is one who:
    - Has had a credit sale within the last 4 years.
    - Or has a debt that was closed within the last 4 years.
    - Or was created within the last 4 years.

    Returns a tuple of (number of customers checked, number of customers deactivated).
    """
    four_years_ago = timezone.now() - timedelta(days=4*365)

    # Subquery to find the last sale date for a customer
    last_sale_date = CreditSale.objects.filter(
        customer=OuterRef('pk')
    ).order_by('-sale_date').values('sale_date')[:1]

    # Subquery to find the last debt close date for a customer
    last_debt_close_date = Debt.objects.filter(
        sale__customer=OuterRef('pk')
    ).order_by('-close_date').values('close_date')[:1]

    # Get all active customers to check
    customers_to_check = Customer.objects.filter(is_active=True)
    total_checked = customers_to_check.count()
    deactivated_count = 0
    
    # Annotate with the latest activity dates
    customers_with_activity = customers_to_check.annotate(
        last_sale=Subquery(last_sale_date, output_field=models.DateTimeField()),
        last_debt_close=Subquery(last_debt_close_date, output_field=models.DateField())
    )

    customers_to_deactivate_pks = []
    for customer in customers_with_activity:
        # Determine the last activity date, considering all might be None
        last_activity_date = customer.created_at
        
        if customer.last_sale:
            # Pytz adds timezone info to the datetime object, so we make created_at aware too
            aware_created_at = timezone.make_aware(
                customer.created_at, timezone.get_default_timezone()
            ) if timezone.is_naive(customer.created_at) else customer.created_at
            last_activity_date = max(aware_created_at, customer.last_sale)

        if customer.last_debt_close:
            # Convert date to datetime to compare with other activity dates
            debt_close_datetime = timezone.make_aware(
                timezone.datetime.combine(customer.last_debt_close, timezone.datetime.min.time())
            )
            last_activity_date = max(last_activity_date, debt_close_datetime)

        # If the last activity was more than 4 years ago, deactivate
        if last_activity_date < four_years_ago:
            customers_to_deactivate_pks.append(customer.pk)

    if customers_to_deactivate_pks:
        deactivated_count = Customer.objects.filter(pk__in=customers_to_deactivate_pks).update(is_active=False)

    return total_checked, deactivated_count


def get_customers_for_user(user) -> models.QuerySet[Customer]:
    """
    Returns a queryset of customers based on the user's permissions.
    - Users with 'customer.list_all' permission can see all customers.
    - Other users (e.g., Commercials) can only see customers assigned to their portfolios.
    """
    # Superuser has all permissions implicitly.
    if user.is_authenticated:
        if user.is_superuser or user.has_permission('customer.list_all'):
            return Customer.objects.all()
        # Fallback for users without the 'list_all' permission (e.g., Commercials)
        return Customer.objects.filter(portfolio__commercial=user)

    # Default to an empty queryset for unauthenticated users
    return Customer.objects.none()