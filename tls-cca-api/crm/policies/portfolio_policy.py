"""Authorization policy for portfolio mutations."""

from rbac.services.permission_resolver import PermissionResolver


class PortfolioPolicy:
    """Centralize authorization for portfolio assignment operations."""

    @staticmethod
    def can_assign(
        actor,
        portfolio,
        target_commercial,
        permission_code="portfolio.assign",
    ):
        """Return whether the actor may perform the requested mutation."""
        if actor is None or actor.is_superuser:
            return True
        return PermissionResolver.has(actor, permission_code)

    @staticmethod
    def can_transfer(actor, portfolio, target_commercial):
        """Return whether the actor may transfer a portfolio."""
        return PortfolioPolicy.can_assign(
            actor,
            portfolio,
            target_commercial,
            permission_code="portfolio.transfer",
        )
