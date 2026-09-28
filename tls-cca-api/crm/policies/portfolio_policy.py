"""Authorization policies for portfolio mutations."""

from rbac.services.permission_resolver import PermissionResolver


class PortfolioPolicy:
    """Keep authorization checks separate from portfolio service mechanics."""

    @staticmethod
    def can_assign(
        actor,
        portfolio,
        target_commercial,
        permission_code="portfolio.assign",
    ):
        if actor is None:
            return True
        if actor.is_superuser:
            return True
        if not PermissionResolver.has(actor, permission_code):
            return False
        return bool(
            target_commercial
            and target_commercial.is_active
            and portfolio.commercial_id != target_commercial.id
        )

    @staticmethod
    def can_transfer(actor, portfolio, target_commercial):
        return PortfolioPolicy.can_assign(
            actor,
            portfolio,
            target_commercial,
            permission_code="portfolio.transfer",
        )
