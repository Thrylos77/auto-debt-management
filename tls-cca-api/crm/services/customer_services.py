"""Customer lifecycle and persistence services."""

from django.db import models, transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.events import (
    customer_activated,
    customer_created,
    customer_deactivated,
    customer_lifecycle_changed,
    customer_updated,
)
from rbac.services.permission_resolver import PermissionResolver

from ..models import (
    Customer,
    CustomerAddress,
    MoralPersonDetail,
    PhysicalPersonDetail,
    Portfolio,
)
from receivables.models import Debt
from sales.models import CreditSale
from ..policies.customer_policy import CustomerPolicy
from .inactivity_policy import get_customer_inactivity_threshold


LIFECYCLE_TRANSITIONS = {
    Customer.LIFECYCLE_PROSPECT: {
        Customer.LIFECYCLE_ACTIVE,
    },
    Customer.LIFECYCLE_ACTIVE: {
        Customer.LIFECYCLE_SUSPENDED,
        Customer.LIFECYCLE_INACTIVE,
    },
    Customer.LIFECYCLE_SUSPENDED: {
        Customer.LIFECYCLE_ACTIVE,
        Customer.LIFECYCLE_BLOCKED,
    },
    Customer.LIFECYCLE_INACTIVE: {
        Customer.LIFECYCLE_ACTIVE,
        Customer.LIFECYCLE_ARCHIVED,
    },
    Customer.LIFECYCLE_BLOCKED: {
        Customer.LIFECYCLE_ACTIVE,
    },
    Customer.LIFECYCLE_ARCHIVED: set(),
}

LIFECYCLE_PERMISSIONS = {
    Customer.LIFECYCLE_ACTIVE: "customer.activate",
    Customer.LIFECYCLE_SUSPENDED: "customer.suspend",
    Customer.LIFECYCLE_INACTIVE: "customer.deactivate",
    Customer.LIFECYCLE_BLOCKED: "customer.block",
    Customer.LIFECYCLE_ARCHIVED: "customer.archive",
}


def create_customer(validated_data: dict, creator=None, request=None) -> Customer:
    """Create a customer and its person detail atomically."""
    with transaction.atomic():
        physical_detail_data = validated_data.pop("physical_detail", None)
        moral_detail_data = validated_data.pop("moral_detail", None)
        addresses_data = validated_data.pop("addresses", None)

        if creator and not validated_data.get("portfolio"):
            portfolio = Portfolio.objects.filter(
                commercial=creator,
                active=True,
            ).first()
            if portfolio:
                validated_data["portfolio"] = portfolio

        # New customers remain active for compatibility with the existing
        # create workflow. Lifecycle-specific changes use explicit actions.
        validated_data.setdefault("lifecycle_status", Customer.LIFECYCLE_ACTIVE)
        validated_data.setdefault("is_active", True)
        validated_data.setdefault("status_changed_at", timezone.now())
        validated_data.setdefault("status_changed_by_id", getattr(creator, "pk", None))
        validated_data.setdefault("status_reason", "Customer created")

        customer = Customer.objects.create(**validated_data)

        if customer.customer_type == Customer.TYPE_PHYSICAL and physical_detail_data:
            PhysicalPersonDetail.objects.create(
                customer=customer,
                **physical_detail_data,
            )
        elif customer.customer_type == Customer.TYPE_MORAL and moral_detail_data:
            MoralPersonDetail.objects.create(
                customer=customer,
                **moral_detail_data,
            )

        if addresses_data:
            _sync_customer_addresses(customer, addresses_data)

        customer_created.send(
            sender=Customer,
            customer=customer,
            actor=creator,
            request=request,
        )
        return customer


@transaction.atomic
def update_customer(
    instance: Customer,
    validated_data: dict,
    *,
    actor=None,
    request=None,
) -> Customer:
    """Update customer data while keeping lifecycle fields service-controlled."""
    for internal_field in (
        "is_active",
        "lifecycle_status",
        "status_changed_at",
        "status_changed_by_id",
        "status_reason",
    ):
        validated_data.pop(internal_field, None)

    physical_detail_data = validated_data.pop("physical_detail", None)
    moral_detail_data = validated_data.pop("moral_detail", None)
    addresses_data = validated_data.pop("addresses", None)

    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()

    if instance.customer_type == Customer.TYPE_PHYSICAL and physical_detail_data:
        PhysicalPersonDetail.objects.update_or_create(
            customer=instance,
            defaults=physical_detail_data,
        )
    elif instance.customer_type == Customer.TYPE_MORAL and moral_detail_data:
        MoralPersonDetail.objects.update_or_create(
            customer=instance,
            defaults=moral_detail_data,
        )

    if addresses_data is not None:
        _sync_customer_addresses(instance, addresses_data)

    customer_updated.send(
        sender=Customer,
        customer=instance,
        actor=actor,
        request=request,
    )
    return instance


def _sync_customer_addresses(customer: Customer, addresses_data: list[dict]) -> None:
    """Create/update submitted addresses without deleting omitted addresses."""
    existing_count = customer.addresses.count()
    primary_exists = customer.addresses.filter(is_primary=True).exists()
    explicit_primary = any(item.get("is_primary") for item in addresses_data)

    for index, address_data in enumerate(addresses_data):
        payload = dict(address_data)
        address_id = payload.pop("id", None)

        if address_id is not None:
            address = CustomerAddress.objects.filter(
                pk=address_id,
                customer=customer,
            ).first()
            if address is None:
                raise ValidationError(
                    "The supplied address does not belong to this customer."
                )
        else:
            address = None

        if payload.get("is_primary"):
            customer.addresses.filter(is_primary=True).exclude(
                pk=getattr(address, "pk", None),
            ).update(is_primary=False)
            primary_exists = True
        elif not primary_exists and not explicit_primary and existing_count == 0 and index == 0:
            payload["is_primary"] = True
            primary_exists = True

        if address is None:
            CustomerAddress.objects.create(
                customer=customer,
                **payload,
            )
        else:
            for field, value in payload.items():
                setattr(address, field, value)
            address.save()


@transaction.atomic
def _transition_customer(
    customer: Customer,
    target_status: str,
    *,
    actor=None,
    request=None,
    reason: str = "",
) -> Customer:
    """Apply one explicitly authorized lifecycle transition atomically."""
    permission_code = LIFECYCLE_PERMISSIONS[target_status]
    locked_customer = Customer.objects.select_for_update().get(pk=customer.pk)

    if not CustomerPolicy.can_transition(
        actor,
        locked_customer,
        permission_code,
    ):
        raise PermissionDenied(
            "You do not have permission to change this customer's lifecycle."
        )

    previous_status = locked_customer.lifecycle_status
    if target_status == previous_status:
        return locked_customer

    allowed_targets = LIFECYCLE_TRANSITIONS.get(previous_status, set())
    if target_status not in allowed_targets:
        raise ValidationError(
            f"Invalid customer lifecycle transition: "
            f"{previous_status} -> {target_status}."
        )

    locked_customer.lifecycle_status = target_status
    locked_customer.is_active = target_status in {
        Customer.LIFECYCLE_PROSPECT,
        Customer.LIFECYCLE_ACTIVE,
    }
    locked_customer.status_changed_at = timezone.now()
    locked_customer.status_changed_by_id = getattr(actor, "pk", None)
    locked_customer.status_reason = reason or ""
    locked_customer.save(
        update_fields=[
            "lifecycle_status",
            "is_active",
            "status_changed_at",
            "status_changed_by_id",
            "status_reason",
        ]
    )

    customer_lifecycle_changed.send(
        sender=Customer,
        customer=locked_customer,
        actor=actor,
        request=request,
        previous_status=previous_status,
        new_status=target_status,
        reason=reason or "",
    )

    if target_status == Customer.LIFECYCLE_ACTIVE:
        customer_activated.send(
            sender=Customer,
            customer=locked_customer,
            actor=actor,
            request=request,
        )
    elif target_status == Customer.LIFECYCLE_INACTIVE:
        customer_deactivated.send(
            sender=Customer,
            customer=locked_customer,
            actor=actor,
            request=request,
        )

    return locked_customer


def activate_customer(customer: Customer, *, actor=None, request=None, reason="") -> Customer:
    """Move a customer to ACTIVE using the explicit lifecycle transition."""
    return _transition_customer(
        customer,
        Customer.LIFECYCLE_ACTIVE,
        actor=actor,
        request=request,
        reason=reason,
    )


def suspend_customer(customer: Customer, *, actor=None, request=None, reason="") -> Customer:
    """Move an ACTIVE customer to SUSPENDED."""
    return _transition_customer(
        customer,
        Customer.LIFECYCLE_SUSPENDED,
        actor=actor,
        request=request,
        reason=reason,
    )


def deactivate_customer(customer: Customer, *, actor=None, request=None, reason="") -> Customer:
    """Move an ACTIVE customer to INACTIVE."""
    return _transition_customer(
        customer,
        Customer.LIFECYCLE_INACTIVE,
        actor=actor,
        request=request,
        reason=reason,
    )


def block_customer(customer: Customer, *, actor=None, request=None, reason="") -> Customer:
    """Move a SUSPENDED customer to BLOCKED."""
    return _transition_customer(
        customer,
        Customer.LIFECYCLE_BLOCKED,
        actor=actor,
        request=request,
        reason=reason,
    )


def unblock_customer(customer: Customer, *, actor=None, request=None, reason="") -> Customer:
    """Unblock a BLOCKED customer by returning it to ACTIVE."""
    return _transition_customer(
        customer,
        Customer.LIFECYCLE_ACTIVE,
        actor=actor,
        request=request,
        reason=reason,
    )


def archive_customer(customer: Customer, *, actor=None, request=None, reason="") -> Customer:
    """Archive an INACTIVE customer."""
    return _transition_customer(
        customer,
        Customer.LIFECYCLE_ARCHIVED,
        actor=actor,
        request=request,
        reason=reason,
    )


def auto_deactivate_inactive_customers() -> tuple[int, int]:
    """Deactivate customers whose most recent business activity is too old."""
    inactivity_threshold = get_customer_inactivity_threshold()

    last_sale_date = CreditSale.objects.filter(
        customer=OuterRef("pk")
    ).order_by("-sale_date").values("sale_date")[:1]

    last_debt_close_date = Debt.objects.filter(
        sale__customer=OuterRef("pk")
    ).order_by("-close_date").values("close_date")[:1]

    customers_to_check = Customer.objects.filter(
        lifecycle_status=Customer.LIFECYCLE_ACTIVE,
    )
    total_checked = customers_to_check.count()
    deactivated_count = 0

    customers_with_activity = customers_to_check.annotate(
        last_sale=Subquery(
            last_sale_date,
            output_field=models.DateTimeField(),
        ),
        last_debt_close=Subquery(
            last_debt_close_date,
            output_field=models.DateField(),
        ),
    )

    customer_ids_to_deactivate = []
    for customer in customers_with_activity:
        last_activity_date = customer.created_at

        if customer.last_sale:
            aware_created_at = (
                timezone.make_aware(
                    customer.created_at,
                    timezone.get_default_timezone(),
                )
                if timezone.is_naive(customer.created_at)
                else customer.created_at
            )
            last_activity_date = max(aware_created_at, customer.last_sale)

        if customer.last_debt_close:
            debt_close_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    customer.last_debt_close,
                    timezone.datetime.min.time(),
                ),
                timezone.utc,
            )
            last_activity_date = max(last_activity_date, debt_close_datetime)

        if last_activity_date < inactivity_threshold:
            customer_ids_to_deactivate.append(customer.pk)

    for customer in Customer.objects.filter(pk__in=customer_ids_to_deactivate):
        deactivate_customer(
            customer,
            actor=None,
            reason="Automatic inactivity policy",
        )
        deactivated_count += 1

    return total_checked, deactivated_count


def get_customers_for_user(user) -> models.QuerySet[Customer]:
    """Return customers inside the authenticated user's CRM scope."""
    if user.is_authenticated:
        if user.is_superuser or PermissionResolver.has(user, "customer.list_all"):
            return Customer.objects.all().order_by("id")
        return Customer.objects.filter(
            portfolio__commercial=user,
        ).order_by("id")

    return Customer.objects.none()
