"""users/tests/test_views.py"""
import pytest
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import User, OTP
from notifications.models import Notification, NotificationDelivery
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
    user.set_password('password123')
    user.save()
    return user

@pytest.fixture
def superuser(user_factory):
    return user_factory.create(is_staff=True, is_superuser=True, password='superpassword')

@pytest.mark.django_db
class TestAuthViews:
    def test_register_user(self, api_client, superuser):
        url = reverse('register')
        api_client.force_authenticate(user=superuser)
        data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password': 'StrongPass123?',
            'password2': 'StrongPass123?'
        }
        response = api_client.post(url, data)
        assert response.status_code == 201
        assert User.objects.filter(username='newuser').exists()

    def test_login_user(self, api_client, user):
        url = reverse('auth-login')
        data = {'identifier': user.username, 'password': 'password123'}
        response = api_client.post(url, data)
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

@pytest.mark.django_db
class TestUserViews:
    def test_get_user_detail_authenticated(self, api_client, user):
        url = reverse('user-detail')
        api_client.force_authenticate(user=user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data['username'] == user.username

    def test_get_user_detail_unauthenticated(self, api_client):
        url = reverse('user-detail')
        response = api_client.get(url)
        assert response.status_code == 401

    def test_list_users_as_superuser(self, api_client, superuser):
        url = reverse('user-list')
        api_client.force_authenticate(user=superuser)
        response = api_client.get(url)
        assert response.status_code == 200

    def test_retrieve_user_as_superuser(self, api_client, superuser, user):
        url = reverse('user-rud', kwargs={'pk': user.pk})
        api_client.force_authenticate(user=superuser)
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data['username'] == user.username

    def test_update_user_as_superuser(self, api_client, superuser, user):
        url = reverse('user-rud', kwargs={'pk': user.pk})
        api_client.force_authenticate(user=superuser)
        data = {'first_name': 'Updated'}
        response = api_client.patch(url, data)
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.first_name == 'Updated'

    def test_deactivate_user_as_superuser(self, api_client, superuser, user):
        url = reverse('user-rud', kwargs={'pk': user.pk})
        api_client.force_authenticate(user=superuser)
        response = api_client.delete(url)
        assert response.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False

    def test_deactivate_user_uses_dedicated_permission(self, api_client, user, user_factory):
        from rbac.models import Permission, Role, RoleAssignment

        actor = user_factory.create(username="deactivate-actor", email="deactivate-actor@example.com")
        permission = Permission.objects.create(
            code="user.deactivate",
            label="Deactivate user",
        )
        role = Role.objects.create(name="deactivate-actor-role")
        role.permissions.add(permission)
        RoleAssignment.objects.create(user=actor, role=role)

        api_client.force_authenticate(user=actor)
        response = api_client.delete(reverse("user-rud", kwargs={"pk": user.pk}))

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False

    def test_deactivate_user_denied_without_dedicated_permission(self, api_client, user, user_factory):
        actor = user_factory.create(
            username="deactivate-denied",
            email="deactivate-denied@example.com",
        )

        api_client.force_authenticate(user=actor)
        response = api_client.delete(reverse("user-rud", kwargs={"pk": user.pk}))

        assert response.status_code == 403
        user.refresh_from_db()
        assert user.is_active is True


@pytest.mark.django_db
class TestPasswordViews:
    def test_change_own_password(self, api_client, user):
        # Grant superuser to bypass specific permission check for this test
        user.is_superuser = True
        user.save()
        
        url = reverse('password-change-self')
        api_client.force_authenticate(user=user)
        data = {
            'old_password': 'password123',
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!'
        }
        response = api_client.put(url, data)
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password('NewPassword123!')

    def test_admin_change_password(self, api_client, superuser, user):
        url = reverse('password-force-reset', kwargs={'pk': user.pk})
        api_client.force_authenticate(user=superuser)
        data = {
            'new_password': 'NewAdminPass123!',
        }
        response = api_client.put(url, data)
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password('NewAdminPass123!')

    def test_request_otp(self, api_client, user):
        url = reverse('auth-password-forgot')
        data = {'email': user.email}
        response = api_client.post(url, data)

        assert response.status_code == 200
        assert OTP.objects.filter(user=user).exists()
        notification = Notification.objects.get(
            user=user,
            code='password_reset_otp',
        )
        assert notification.category == Notification.SECURITY
        delivery = NotificationDelivery.objects.get(
            notification=notification,
            channel=NotificationDelivery.CHANNEL_EMAIL,
        )
        assert delivery.status == NotificationDelivery.STATUS_SENT

    def test_reset_password_with_otp(self, api_client, user):
        otp = OTP.objects.create(
            user=user,
            code_hash=make_password('654321'),
            expires_at=timezone.now() + timedelta(minutes=OTP.EXPIRATION_MINUTES),
        )
        url = reverse('auth-password-reset')
        data = {
            'email': user.email,
            'otp': '654321',
            'new_password': 'ResetPass123!',
            'new_password2': 'ResetPass123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password('ResetPass123!')
        otp.refresh_from_db()
        assert otp.is_used is True

@pytest.mark.django_db
class TestHistoryViews:
    def test_get_user_history_as_superuser(self, api_client, superuser, user):
        user.first_name = 'History'
        user.save()
        url = reverse('user-history-detail', kwargs={'pk': user.pk})
        api_client.force_authenticate(user=superuser)
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) > 0 # Should have at least one history record

    def test_get_all_users_history_as_superuser(self, api_client, superuser):
        url = reverse('user-history-list')
        api_client.force_authenticate(user=superuser)
        response = api_client.get(url)
        assert response.status_code == 200
