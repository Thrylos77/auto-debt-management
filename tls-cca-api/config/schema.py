"""OpenAPI preprocessing helpers."""


LEGACY_PATH_PREFIXES = (
    "/api/core/",
    "/api/users/",
    "/api/permissions/",
    "/api/roles/",
    "/api/groups/",
    "/api/crm/",
    "/api/sales/",
    "/api/receivables/",
    "/api/reporting/",
    "/api/audit/",
    "/api/token/",
)


def remove_legacy_paths(endpoints):
    """Keep legacy compatibility routes out of the canonical OpenAPI schema."""

    return [
        endpoint
        for endpoint in endpoints
        if not endpoint[0].startswith(LEGACY_PATH_PREFIXES)
    ]
