"""RBAC policies fail closed for unauthenticated/unauthorized users."""

import pytest
from django.contrib.auth import get_user_model

from rbac.models import Permission, Role, RoleAssignment
from vehicles.policies import InventoryPolicy, ReservationPolicy, VehiclePolicy


@pytest.mark.django_db
class TestVehiclePolicies:
    def _user_with_permissions(self, *codes):
        User = get_user_model()
        user = User.objects.create_user(
            username=f"vpol_{abs(hash(codes))}",
            email=f"vpol_{abs(hash(codes))}@example.com",
            password="pw",
            is_active=True,
        )
        role = Role.objects.create(name=f"VROLE_{abs(hash((codes, user.pk)))}")
        for code in codes:
            permission = Permission.objects.create(code=code, label=code)
            role.permissions.add(permission)
        RoleAssignment.objects.create(user=user, role=role)
        return user

    def test_vehicle_create_fails_without_permission(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="vno", email="vno@example.com", password="pw", is_active=True
        )
        assert VehiclePolicy.can_create(user) is False
        assert ReservationPolicy.can_list(user) is False
        assert InventoryPolicy.can_validate(user) is False

    def test_vehicle_create_succeeds_with_explicit_permission(self):
        user = self._user_with_permissions("vehicle.create")
        assert VehiclePolicy.can_create(user) is True
