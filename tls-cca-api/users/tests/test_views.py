"""Regression tests for User, authentication, password, and history views."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import User
from users.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def user(user_factory):
    user = user_factory.create()
    user.set_password("OldPassword123!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def superuser(user_factory):
    user = user_factory.create(
        is_staff=True,
        is_superuser=True,
    )
    user.set_password("SuperPassword123!")
    user.save(update_fields=["password"])
    return user


@pytest.mark.django_db
class TestAuthViews:
    def test_register_user_creates_invited_account(self, api_client, superuser):
        url = reverse("register")
        api_client.force_authenticate(user=superuser)
        data = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == 201
        created = User.objects.get(username="newuser")
        assert created.is_active is False
        assert created.account_status == "invited"
        assert created.has_usable_password() is False

    def test_login_without_totp_requires_enrollment(self, api_client, user):
        response = api_client.post(
            reverse("auth-login"),
            {
                "identifier": user.username,
                "password": "OldPassword123!",
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["requires_2fa_setup"] is True
        assert "access" not in response.data
        assert "refresh" not in response.data


@pytest.mark.django_db
class TestUserViews:
    def test_get_user_detail_authenticated(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get(reverse("user-detail"))

        assert response.status_code == 200
        assert response.data["username"] == user.username

    def test_get_user_detail_unauthenticated(self, api_client):
        response = api_client.get(reverse("user-detail"))
        assert response.status_code == 401

    def test_list_users_as_superuser(self, api_client, superuser):
        api_client.force_authenticate(user=superuser)
        response = api_client.get(reverse("user-list"))
        assert response.status_code == 200

    def test_retrieve_user_as_superuser(self, api_client, superuser, user):
        api_client.force_authenticate(user=superuser)
        response = api_client.get(
            reverse("user-rud", kwargs={"pk": user.pk})
        )

        assert response.status_code == 200
        assert response.data["username"] == user.username

    def test_update_user_as_superuser(self, api_client, superuser, user):
        api_client.force_authenticate(user=superuser)
        response = api_client.patch(
            reverse("user-rud", kwargs={"pk": user.pk}),
            {"first_name": "Updated"},
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "Updated"

    def test_deactivate_user_as_superuser(self, api_client, superuser, user):
        api_client.force_authenticate(user=superuser)
        response = api_client.delete(
            reverse("user-rud", kwargs={"pk": user.pk})
        )

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False
        assert user.account_status == "disabled"

    def test_deactivate_user_uses_dedicated_permission(
        self,
        api_client,
        user,
        user_factory,
    ):
        from rbac.models import Permission, Role, RoleAssignment

        actor = user_factory.create(
            username="deactivate-actor",
            email="deactivate-actor@example.com",
        )
        permission = Permission.objects.create(
            code="user.deactivate",
            label="Deactivate user",
        )
        role = Role.objects.create(name="deactivate-actor-role")
        role.permissions.add(permission)
        RoleAssignment.objects.create(user=actor, role=role)

        api_client.force_authenticate(user=actor)
        response = api_client.delete(
            reverse("user-rud", kwargs={"pk": user.pk})
        )

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False

    def test_deactivate_user_denied_without_dedicated_permission(
        self,
        api_client,
        user,
        user_factory,
    ):
        actor = user_factory.create(
            username="deactivate-denied",
            email="deactivate-denied@example.com",
        )

        api_client.force_authenticate(user=actor)
        response = api_client.delete(
            reverse("user-rud", kwargs={"pk": user.pk})
        )

        assert response.status_code == 403
        user.refresh_from_db()
        assert user.is_active is True


@pytest.mark.django_db
class TestHistoryViews:
    def test_get_user_history_as_superuser(self, api_client, superuser, user):
        user.first_name = "History"
        user.save(update_fields=["first_name"])
        api_client.force_authenticate(user=superuser)

        response = api_client.get(
            reverse("user-history-detail", kwargs={"pk": user.pk})
        )

        assert response.status_code == 200
        assert len(response.data) > 0

    def test_get_all_users_history_as_superuser(self, api_client, superuser):
        api_client.force_authenticate(user=superuser)
        response = api_client.get(reverse("user-history-list"))
        assert response.status_code == 200
