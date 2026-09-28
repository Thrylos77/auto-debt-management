"""Signals handling internal portfolio redistribution on user deactivation."""

from django.dispatch import receiver

from core.events import user_deactivated

from .services.portfolio_services import transfer_active_portfolios_of_commercial


@receiver(user_deactivated)
def transfer_portfolios_on_user_deactivated(
    sender,
    user,
    successor_user=None,
    reason=None,
    actor=None,
    **kwargs,
):
    """Transfer active portfolios as an internal deactivation side effect."""
    if successor_user is None:
        return

    # The transfer is a trusted consequence of the already-authorized user
    # deactivation. It must not require a separate portfolio permission.
    transfer_active_portfolios_of_commercial(
        from_commercial=user,
        to_commercial=successor_user,
        transferred_by=None,
        reason=reason or f"Leaving commercial '{user}' deactivated",
    )
