"""Portfolio assignment and transfer services."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.events import portfolio_assigned, portfolio_created, portfolio_transferred
from crm.models import Portfolio, PortfolioTransfer
from crm.policies.portfolio_policy import PortfolioPolicy

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser as UserType
else:
    UserType = get_user_model()


def _generate_next_portfolio_ref() -> str:
    """Generate the next available portfolio reference."""
    last_portfolio = Portfolio.objects.order_by("id").last()
    if not last_portfolio or not last_portfolio.ref.startswith("PF-"):
        return "PF-001"

    try:
        last_id = int(last_portfolio.ref.split("-")[-1])
        return f"PF-{last_id + 1:03d}"
    except (ValueError, IndexError):
        return f"PF-{(last_portfolio.id or 0) + 1:03d}"


@transaction.atomic
def create_portfolio_for_commercial(
    commercial: UserType,
    description: str = None,
) -> Portfolio:
    """Create a portfolio with an auto-generated reference."""
    ref = _generate_next_portfolio_ref()
    description = description or (
        f"Main portfolio for "
        f"{commercial.get_full_name() or commercial.username}"
    )

    portfolio = Portfolio.objects.create(
        ref=ref,
        commercial=commercial,
        description=description,
    )
    portfolio_created.send(
        sender=Portfolio,
        portfolio=portfolio,
        actor=commercial,
    )
    return portfolio


@transaction.atomic
def assign_portfolio(
    portfolio: Portfolio,
    to_commercial: UserType,
    transferred_by: Optional[UserType] = None,
    reason: str = None,
    required_permission: str = "portfolio.assign",
) -> Portfolio:
    """Assign an active portfolio and append an immutable transfer entry."""
    if to_commercial is None:
        raise ValidationError("A target commercial is required to assign a portfolio.")

    locked_portfolio = (
        Portfolio.objects
        .select_for_update()
        .select_related("commercial")
        .get(pk=portfolio.pk)
    )

    if not PortfolioPolicy.can_assign(
        transferred_by,
        locked_portfolio,
        to_commercial,
        permission_code=required_permission,
    ):
        raise PermissionDenied(
            "You do not have permission to modify this portfolio."
        )

    if not locked_portfolio.active:
        raise ValidationError(
            f"Portfolio '{locked_portfolio.ref}' is inactive and cannot be assigned."
        )

    if not to_commercial.is_active:
        raise ValidationError(
            f"Commercial '{to_commercial}' is inactive and cannot receive a portfolio."
        )

    if locked_portfolio.commercial_id == to_commercial.id:
        raise ValidationError(
            f"Portfolio '{locked_portfolio.ref}' is already assigned to '{to_commercial}'."
        )

    from_commercial = locked_portfolio.commercial
    locked_portfolio.commercial = to_commercial
    locked_portfolio.save(update_fields=["commercial", "last_transfer_date"])

    transfer_reason = reason or (
        f"Assigned from {from_commercial or 'unassigned'} to {to_commercial}"
        if from_commercial
        else f"Assigned to {to_commercial}"
    )

    PortfolioTransfer.objects.create(
        portfolio=locked_portfolio,
        from_commercial=from_commercial,
        to_commercial=to_commercial,
        transferred_by=transferred_by,
        reason=transfer_reason,
    )
    portfolio_assigned.send(
        sender=Portfolio,
        portfolio=locked_portfolio,
        actor=transferred_by,
        from_commercial=from_commercial,
        to_commercial=to_commercial,
        reason=transfer_reason,
    )
    return locked_portfolio


@transaction.atomic
def transfer_portfolio(
    portfolio: Portfolio,
    to_commercial: UserType,
    transferred_by: Optional[UserType] = None,
    reason: str = None,
) -> Portfolio:
    """Transfer one active portfolio to another active commercial."""
    result = assign_portfolio(
        portfolio,
        to_commercial,
        transferred_by=transferred_by,
        reason=reason,
        required_permission="portfolio.transfer",
    )
    portfolio_transferred.send(
        sender=Portfolio,
        portfolio=result,
        actor=transferred_by,
        to_commercial=to_commercial,
        reason=reason or "Portfolio transferred",
    )
    return result


@transaction.atomic
def transfer_active_portfolios_of_commercial(
    from_commercial: UserType,
    to_commercial: UserType,
    transferred_by: Optional[UserType] = None,
    reason: str = None,
) -> List[Portfolio]:
    """Transfer all active portfolios owned by a departing commercial."""
    if to_commercial is None:
        raise ValidationError(
            "A target commercial is required to transfer portfolios."
        )
    if not to_commercial.is_active:
        raise ValidationError(
            f"Commercial '{to_commercial}' is inactive and cannot receive portfolios."
        )

    transfer_reason = reason or (
        f"Transfer of leaving commercial '{from_commercial}' portfolios"
    )
    portfolios = Portfolio.objects.filter(
        commercial=from_commercial,
        active=True,
    )

    transferred: List[Portfolio] = []
    for portfolio in portfolios:
        if portfolio.commercial_id == to_commercial.id:
            continue
        transferred.append(
            assign_portfolio(
                portfolio,
                to_commercial,
                transferred_by=transferred_by,
                reason=transfer_reason,
                required_permission="portfolio.transfer",
            )
        )
    return transferred
