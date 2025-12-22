# crm/services/portfolio_services.py
from typing import TYPE_CHECKING
from __future__ import annotations # For compatibility with type hints
from django.db import transaction
from django.contrib.auth import get_user_model

from crm.models import Portfolio

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