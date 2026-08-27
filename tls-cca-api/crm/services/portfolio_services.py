# crm/services/portfolio_services.py
from __future__ import annotations # For compatibility with type hints
from typing import TYPE_CHECKING, List, Optional

from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from crm.models import Portfolio, PortfolioTransfer

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser as UserType
else:
    User = get_user_model()
    UserType = User

def _generate_next_portfolio_ref() -> str:
    """
    Generates the next available portfolio reference (e.g., PF-001, PF-002).
    """
    last_portfolio = Portfolio.objects.order_by('id').last()
    if not last_portfolio or not last_portfolio.ref.startswith('PF-'):
        return 'PF-001'
    
    try:
        last_id = int(last_portfolio.ref.split('-')[-1])
        new_id = last_id + 1
        return f'PF-{new_id:03d}'
    except (ValueError, IndexError):
        # Fallback in case of unexpected format
        return f'PF-{(last_portfolio.id or 0) + 1:03d}'

@transaction.atomic
def create_portfolio_for_commercial(commercial: UserType, description: str = None) -> Portfolio:
    """
    Creates a new portfolio with an auto-generated reference for a given commercial user.
    """
    ref = _generate_next_portfolio_ref()
    description = description or f"Main portfolio for {commercial.get_full_name() or commercial.username}"
    
    portfolio = Portfolio.objects.create(
        ref=ref,
        commercial=commercial,
        description=description
    )
    return portfolio


@transaction.atomic
def assign_portfolio(
    portfolio: Portfolio,
    to_commercial: UserType,
    transferred_by: Optional[UserType] = None,
    reason: str = None,
) -> Portfolio:
    """
    Assigns an existing portfolio to a target commercial.

    Business rules :
    - The target commercial must be active.
    - The portfolio cannot be re-assigned to the commercial who already owns it.
    - The portfolio is marked active.
    - A `PortfolioTransfer` journal entry is recorded (from/to/reason/actor/date).
    """
    if to_commercial is None:
        raise ValidationError("A target commercial is required to assign a portfolio.")
    if not to_commercial.is_active:
        raise ValidationError(
            f"Commercial '{to_commercial}' is inactive and cannot receive a portfolio."
        )
    if portfolio.commercial_id == to_commercial.id:
        raise ValidationError(
            f"Portfolio '{portfolio.ref}' is already assigned to '{to_commercial}'."
        )

    from_commercial = portfolio.commercial

    portfolio.commercial = to_commercial
    portfolio.active = True
    portfolio.save()

    reason = reason or (
        f"Assigned from {from_commercial or 'unassigned'} to {to_commercial}"
        if from_commercial
        else f"Assigned to {to_commercial}"
    )

    PortfolioTransfer.objects.create(
        portfolio=portfolio,
        from_commercial=from_commercial,
        to_commercial=to_commercial,
        transferred_by=transferred_by,
        reason=reason,
    )
    return portfolio


@transaction.atomic
def transfer_portfolio(
    portfolio: Portfolio,
    to_commercial: UserType,
    transferred_by: Optional[UserType] = None,
    reason: str = None,
) -> Portfolio:
    """
    Transfers a single portfolio to a new commercial.

    Used for the "leaving commercial" scenario where a portfolio must be
    handed over to another commercial. Delegates to :func:`assign_portfolio`.
    """
    return assign_portfolio(
        portfolio,
        to_commercial,
        transferred_by=transferred_by,
        reason=reason,
    )


@transaction.atomic
def transfer_active_portfolios_of_commercial(
    from_commercial: UserType,
    to_commercial: UserType,
    transferred_by: Optional[UserType] = None,
    reason: str = None,
) -> List[Portfolio]:
    """
    Transfers all active portfolios owned by a commercial to a target commercial.

    Typically invoked when a commercial is leaving/departing and their
    portfolios must be redistributed before deactivating the user.
    Returns the list of portfolios that were effectively transferred.
    """
    if to_commercial is None:
        raise ValidationError("A target commercial is required to transfer portfolios.")
    if not to_commercial.is_active:
        raise ValidationError(
            f"Commercial '{to_commercial}' is inactive and cannot receive portfolios."
        )

    reason = reason or f"Transfer of leaving commercial '{from_commercial}' portfolios"

    portfolios = Portfolio.objects.filter(commercial=from_commercial, active=True)
    transferred: List[Portfolio] = []
    for portfolio in portfolios:
        if portfolio.commercial_id == to_commercial.id:
            continue
        transferred.append(
            assign_portfolio(
                portfolio,
                to_commercial,
                transferred_by=transferred_by,
                reason=reason,
            )
        )
    return transferred