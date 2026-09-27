from django.dispatch import receiver

from users.events import user_deactivated

from .services.portfolio_services import transfer_active_portfolios_of_commercial


@receiver(user_deactivated)
def transfer_portfolios_on_user_deactivated(sender, user, successor_user=None, reason=None, actor=None, **kwargs):
    if successor_user is None:
        return
    transfer_active_portfolios_of_commercial(
        from_commercial=user,
        to_commercial=successor_user,
        transferred_by=actor or user,
        reason=reason or f"Leaving commercial '{user}' deactivated",
    )
