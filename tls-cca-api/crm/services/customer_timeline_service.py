"""Build a customer activity timeline from existing audit events."""

from audit.models import AuditEvent
from crm.models import Customer
from sales.models import CreditSale
from receivables.models import Recovery

from crm.policies.customer_policy import CustomerPolicy


class CustomerTimelineService:
    """Read-only aggregator over the existing audit projection."""

    DIRECT_ACTIONS = {
        "customer.create",
        "customer.update",
        "customer.activate",
        "customer.deactivate",
        "customer.lifecycle_changed",
        "customer.suspend",
        "customer.block",
        "customer.archive",
        "customer.unblock",
    }
    PORTFOLIO_ACTIONS = {
        "portfolio.assign",
        "portfolio.assigned",
        "portfolio.transfer",
        "portfolio.transferred",
    }
    SALE_ACTIONS = {
        "creditsale.created",
        "credit_sale.created",
        "creditsale.status_change",
        "credit_sale.status_changed",
    }

    @classmethod
    def get_events(cls, *, actor, customer: Customer):
        """Return timeline audit events after enforcing the customer scope."""
        if not CustomerPolicy.can_view_timeline(actor, customer):
            return AuditEvent.objects.none()

        direct_events = AuditEvent.objects.filter(
            resource_type="Customer",
            resource_id=str(customer.pk),
            action__in=cls.DIRECT_ACTIONS,
        )

        portfolio_ids = set(
            Customer.history
            .filter(id=customer.pk)
            .exclude(portfolio_id=None)
            .values_list("portfolio_id", flat=True)
        )
        if customer.portfolio_id:
            portfolio_ids.add(customer.portfolio_id)

        portfolio_events = AuditEvent.objects.filter(
            resource_type="Portfolio",
            resource_id__in=[str(portfolio_id) for portfolio_id in portfolio_ids],
            action__in=cls.PORTFOLIO_ACTIONS,
        )

        sale_ids = CreditSale.objects.filter(customer=customer).values_list("pk", flat=True)
        sale_events = AuditEvent.objects.filter(
            resource_type="CreditSale",
            resource_id__in=sale_ids,
            action__in=cls.SALE_ACTIONS,
        )

        recovery_ids = Recovery.objects.filter(
            term__debt__sale__customer=customer,
        ).values_list("pk", flat=True)
        recovery_events = AuditEvent.objects.filter(
            resource_type="Recovery",
            resource_id__in=recovery_ids,
            action__in={"recovery.create", "recovery.created"},
        )

        return (
            direct_events
            | portfolio_events
            | sale_events
            | recovery_events
        ).select_related("actor_user").order_by("-occurred_at", "-id")

    @staticmethod
    def serialize_event(event):
        """Map an audit event to the public timeline representation."""
        return {
            "id": event.id,
            "occurred_at": event.occurred_at,
            "action": event.action,
            "status": event.status,
            "reason": event.reason,
            "actor_id": event.actor_user_id,
            "actor_name": (
                event.actor_user.get_full_name()
                or event.actor_user.username
                if event.actor_user
                else "System"
            ),
            "metadata": event.metadata,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
        }
