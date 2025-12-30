import pytest
from users.models import User, OTP
from django.utils import timezone
from datetime import timedelta

@pytest.mark.django_db
def test_user_creation():
    """
    Test that a user can be created.
    """
    user = User.objects.create_user(
        username='testuser',
        first_name='Test',
        last_name='User',
        email='testuser@example.com',
        password='password123'
    )
    assert user.username == 'testuser'
    assert user.first_name == 'Test'
    assert user.last_name == 'User'
    assert user.email == 'testuser@example.com'
    assert user.check_password('password123')
    assert str(user) == "Test User testuser"

@pytest.mark.django_db
def test_otp_creation():
    """
    Test that an OTP can be created for a user.
    """
    user = User.objects.create_user(
        username='otpuser', 
        email='otp@example.com', 
        password='password'
    )
    otp = OTP.objects.create(user=user, code='123456')

    assert otp.user == user
    assert otp.code == '123456'
    assert otp.is_used is False
    assert otp.is_valid() is True
    assert str(otp) == f"OTP for {user} created at {otp.created_at}"

@pytest.mark.django_db
def test_otp_is_valid_method():
    """
    Test the is_valid() method of the OTP model.
    """
    user = User.objects.create_user(
        username='validotp', 
        email='validotp@example.com', 
        password='password')
    # Test a valid OTP
    valid_otp = OTP.objects.create(user=user, code='123456')
    assert valid_otp.is_valid() is True

    # Test an expired OTP
    expired_otp = OTP.objects.create(user=user, code='654321')
    expired_otp.created_at = timezone.now() - timedelta(minutes=OTP.EXPIRATION_MINUTES + 1)
    expired_otp.save()
    assert expired_otp.is_valid() is False

    # Test a used OTP
    used_otp = OTP.objects.create(user=user, code='112233', is_used=True)
    assert used_otp.is_valid() is False
