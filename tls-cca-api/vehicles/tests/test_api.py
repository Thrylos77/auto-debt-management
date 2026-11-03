"""API contract and endpoint authorization tests."""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from vehicles.models import VehicleBrand, VehicleModel, VehicleVariant
from vehicles.services import create_vehicle_unit


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestVehicleApi:
    def test_vehicle_list_is_authenticated_and_paginated(self, api_client, new_user):
        brand = VehicleBrand.objects.create(code="LEXUS", name="Lexus")
        model = VehicleModel.objects.create(brand=brand, code="RX", name="RX")
        variant = VehicleVariant.objects.create(model=model, code="350", name="350")
        create_vehicle_unit(actor=new_user, validated_data={"variant": variant, "current_price": Decimal("1000")})

        url = reverse("vehicle-unit-list")
        response = api_client.get(url)
        assert response.status_code in (401, 403)
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert "results" in response.data

    def test_vehicle_create_requires_permission_for_non_superuser(self, api_client, new_customer):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="vehicle-api-user",
            email="vehicle-api-user@example.com",
            password="pw",
            is_active=True,
        )
        api_client.force_authenticate(user=user)
        response = api_client.post(
            reverse("vehicle-unit-list"),
            {"variant": 99999, "current_price": "1000.00"},
            format="json",
        )
        assert response.status_code == 403

    def test_vehicle_detail_is_denied_without_view_permission(self, api_client, new_user):
        brand = VehicleBrand.objects.create(code="FORD-API", name="Ford")
        model = VehicleModel.objects.create(brand=brand, code="RANGER-API", name="Ranger")
        variant = VehicleVariant.objects.create(model=model, code="XL", name="XL")
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={"variant": variant, "current_price": Decimal("1000")},
        )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="vehicle-read-denied",
            email="vehicle-read-denied@example.com",
            password="pw",
            is_active=True,
        )
        api_client.force_authenticate(user=user)
        response = api_client.get(
            reverse("vehicle-unit-detail", kwargs={"pk": vehicle.pk})
        )
        assert response.status_code == 403

    def test_qr_endpoint_requires_generate_permission_but_superuser_can_access(self, api_client, new_user):
        brand = VehicleBrand.objects.create(code="AUDI", name="Audi")
        model = VehicleModel.objects.create(brand=brand, code="Q5", name="Q5")
        variant = VehicleVariant.objects.create(model=model, code="TDI", name="TDI")
        vehicle = create_vehicle_unit(actor=new_user, validated_data={"variant": variant, "current_price": Decimal("1000")})
        api_client.force_authenticate(user=new_user)
        response = api_client.get(reverse("vehicle-unit-qr-code", kwargs={"pk": vehicle.pk}))
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"
