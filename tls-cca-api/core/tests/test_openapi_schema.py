"""Regression tests for OpenAPI generation."""

import logging

from drf_spectacular.generators import SchemaGenerator


EXPECTED_HISTORY_OPERATION_IDS = {
    "rbac_permission_history_detail",
    "rbac_permission_history_list",
    "rbac_role_history_detail",
    "rbac_role_history_list",
    "rbac_group_history_detail",
    "rbac_group_history_list",
}


def _schema_operations(schema):
    """Yield every HTTP operation from the generated OpenAPI document."""

    for path_item in schema["paths"].values():
        for method, operation in path_item.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                yield operation


def test_openapi_generation_excludes_legacy_routes_and_keeps_v1_contract(caplog):
    """The canonical schema must not contain duplicate legacy operations."""

    caplog.set_level(logging.ERROR)

    schema = SchemaGenerator().get_schema(request=None, public=True)
    paths = schema["paths"]
    operation_ids = [
        operation.get("operationId")
        for operation in _schema_operations(schema)
    ]

    assert "/api/v1/rbac/roles/" in paths
    assert "/api/v1/rbac/roles/history/" in paths
    assert any(
        path.startswith("/api/v1/rbac/roles/history/")
        and path != "/api/v1/rbac/roles/history/"
        for path in paths
    )

    assert "/api/v1/users/" in paths

    legacy_prefixes = (
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
    assert not any(
        path.startswith(prefix)
        for path in paths
        for prefix in legacy_prefixes
    )

    assert len(operation_ids) == len(set(operation_ids))
    assert EXPECTED_HISTORY_OPERATION_IDS.issubset(set(operation_ids))

    assert not any(
        "using @extend_schema on viewset class" in record.getMessage()
        for record in caplog.records
    )
