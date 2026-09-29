import pytest
from django.utils import timezone
from datetime import timedelta

from users.models import AccountInvitation, AccountStatus, PasswordResetChallenge, User


@pytest.mark.django_db
def test_user_creation_keeps_identity_fields():
    user = User.objects.create_user(
        username="testuser",
        first_name="Test",
        last_name="User",
        email="testuser@example.com",
        password="password123",
    )

    assert user.username == "testuser"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.email == "testuser@example.com"
    assert user.check_password("password123")
    assert user.account_status == AccountStatus.ACTIVE
    assert str(user) == "Test User testuser"


@pytest.mark.django_db
def test_security_challenges_have_expiring_lifecycles():
    user = User.objects.create_user(
        username="security-user",
        email="security@example.com",
        password="password",
    )
    invitation = AccountInvitation.objects.create(
        user=user,
        token_hash="a" * 64,
        expires_at=timezone.now() + timedelta(hours=48),
    )
    reset = PasswordResetChallenge.objects.create(
        user=user,
        token_hash="b" * 64,
        purpose=PasswordResetChallenge.SELF_SERVICE,
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    assert invitation.used_at is None
    assert invitation.expires_at > timezone.now()
    assert reset.used_at is None
    assert reset.expires_at > timezone.now()
