"""End-to-end tests for mandatory MFA enrollment and secure recovery."""

from unittest.mock import patch

import pytest
import pyotp
from django.urls import reverse
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.test import APIClient, APIRequestFactory

from notifications.services import NotificationService
from rbac.models import Permission, Role, RoleAssignment
from users.models import AccountStatus, PasswordResetChallenge, TwoFASetup, UserSecurityProfile, UserSession
from users.services.authentication import AuthenticationService
from users.services.invitation_service import InvitationService
from users.services.password_recovery_service import PasswordRecoveryService
from users.services.twofa_service import TwoFAService, encrypt_secret
from users.tests.factories import UserFactory


ACTIVE_TEST_PASSWORD = "TlsCca!Active-2026-X7q9"
INVITATION_TEST_PASSWORD = "TlsCca!Invite-2026-X7q9"


def create_active_user(*, username, email, password=ACTIVE_TEST_PASSWORD, **extra):
    user = UserFactory.create(username=username, email=email, **extra)
    user.set_password(password)
    user.save(update_fields=["password"])
    return user


def create_invited_user(*, username, email, **extra):
    user = UserFactory.create(username=username, email=email, **extra)
    user.set_unusable_password()
    user.is_active = False
    user.account_status = AccountStatus.INVITED
    user.save(update_fields=["password", "is_active", "account_status"])
    return user


def enable_totp(user, secret="JBSWY3DPEHPK3PXP"):
    profile = UserSecurityProfile.objects.get(user=user)
    profile.two_factor_enabled = True
    profile.totp_secret_encrypted = encrypt_secret(secret)
    profile.save(update_fields=["two_factor_enabled", "totp_secret_encrypted"])
    return secret


def grant_permission(user, code):
    permission, _ = Permission.objects.get_or_create(
        code=code,
        defaults={"label": code},
    )
    role = Role.objects.create(name=f"test-{user.pk}-{code.replace('.', '-')}")
    role.permissions.add(permission)
    RoleAssignment.objects.create(user=user, role=role)


@pytest.mark.django_db
class TestMandatoryMFAEnrollment:
    def test_admin_created_account_starts_invited_and_sends_email(self):
        admin = create_active_user(
            username="onboarding-admin",
            email="onboarding-admin@example.com",
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=["is_staff", "is_superuser"])

        from users.services.user_service import create_user

        with patch.object(NotificationService, "notify_account_invitation") as notify:
            user = create_user(
                {
                    "username": "invited-user",
                    "email": "invited@example.com",
                    "first_name": "Invited",
                    "last_name": "User",
                },
                actor=admin,
            )

        assert user.account_status == AccountStatus.INVITED
        assert user.is_active is False
        assert user.has_usable_password() is False
        notify.assert_called_once()

    def test_invitation_acceptance_requires_second_step(self):
        user = create_invited_user(
            username="invitation-user",
            email="invitation@example.com",
        )
        captured = {}

        with patch.object(
            NotificationService,
            "notify_account_invitation",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            InvitationService().issue(user)

        setup = InvitationService().accept(
            captured["token"],
            INVITATION_TEST_PASSWORD,
        )

        user.refresh_from_db()
        assert user.account_status == AccountStatus.PASSWORD_SET
        assert user.is_active is False
        assert user.check_password(INVITATION_TEST_PASSWORD)
        assert setup["two_factor_required"] is True
        assert setup["setup_token"]
        setup_id, raw_setup_token = setup["setup_token"].split(".", 1)
        setup_row = TwoFASetup.objects.get(pk=setup_id)
        assert setup_row.setup_token_hash != raw_setup_token
        assert setup["qrcode"].startswith("data:image/png;base64,")

    def test_invitation_totp_verification_activates_account_and_issues_session(self):
        user = create_invited_user(
            username="invitation-active",
            email="invitation-active@example.com",
        )
        captured = {}

        with patch.object(
            NotificationService,
            "notify_account_invitation",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            InvitationService().issue(user)

        setup = InvitationService().accept(
            captured["token"],
            INVITATION_TEST_PASSWORD,
        )
        code = pyotp.TOTP(setup["secret"]).now()

        response = APIClient().post(
            reverse("auth-invitation-verify-2fa"),
            {"setup_token": setup["setup_token"], "code": code},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["access"]
        assert response.data["refresh"]
        user.refresh_from_db()
        assert user.account_status == AccountStatus.ACTIVE
        assert user.is_active is True
        assert UserSession.objects.filter(user=user, revoked_at__isnull=True).exists()

    def test_existing_active_user_without_totp_cannot_get_a_session(self):
        user = create_active_user(
            username="legacy-active",
            email="legacy-active@example.com",
        )

        response = APIClient().post(
            reverse("auth-login"),
            {
                "identifier": user.email,
                "password": ACTIVE_TEST_PASSWORD,
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["requires_2fa_setup"] is True
        assert "access" not in response.data
        assert "refresh" not in response.data
        assert UserSession.objects.filter(user=user).count() == 0

    def test_existing_user_can_complete_mandatory_totp_enrollment(self):
        user = create_active_user(
            username="initial-enrollment",
            email="initial-enrollment@example.com",
        )
        login_response = APIClient().post(
            reverse("auth-login"),
            {
                "identifier": user.email,
                "password": ACTIVE_TEST_PASSWORD,
            },
            format="json",
        )
        code = pyotp.TOTP(login_response.data["secret"]).now()

        response = APIClient().post(
            reverse("auth-2fa-enroll-verify"),
            {
                "setup_token": login_response.data["setup_token"],
                "code": code,
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["access"]
        user.refresh_from_db()
        assert user.account_status == AccountStatus.ACTIVE
        assert user.is_active is True


@pytest.mark.django_db
class TestAuthenticationAndPasswordRecovery:
    def test_jwt_authentication_rejects_active_user_without_mfa(self):
        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.tokens import RefreshToken
        from users.authentication import EnforcedJWTAuthentication

        user = create_active_user(
            username="jwt-without-mfa",
            email="jwt-without-mfa@example.com",
        )
        refresh = RefreshToken.for_user(user)
        request = APIRequestFactory().get(
            "/api/v1/users/me/",
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}",
        )

        with pytest.raises(AuthenticationFailed):
            EnforcedJWTAuthentication().authenticate(request)

    def test_jwt_authentication_rejects_active_user_without_totp_secret(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        from users.authentication import EnforcedJWTAuthentication

        user = create_active_user(
            username="jwt-no-secret",
            email="jwt-no-secret@example.com",
        )
        profile = UserSecurityProfile.objects.get(user=user)
        profile.two_factor_enabled = True
        profile.totp_secret_encrypted = None
        profile.save(update_fields=["two_factor_enabled", "totp_secret_encrypted"])

        token = RefreshToken.for_user(user).access_token
        request = APIRequestFactory().get("/api/v1/auth/verify/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"

        with pytest.raises(AuthenticationFailed):
            EnforcedJWTAuthentication().authenticate(request)

    def test_issue_tokens_requires_enabled_totp_even_when_account_status_is_active(self):
        user = create_active_user(
            username="token-without-totp",
            email="token-without-totp@example.com",
        )
        with pytest.raises(AuthenticationFailed):
            AuthenticationService().issue_tokens(user)

    def test_refresh_is_rejected_when_mfa_is_not_enabled(self):
        user = create_active_user(
            username="refresh-without-mfa",
            email="refresh-without-mfa@example.com",
        )
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        response = APIClient().post(
            reverse("auth-refresh"),
            {"refresh": str(refresh)},
            format="json",
        )
        assert response.status_code == 401

    def test_invitation_token_is_single_use(self):
        user = create_invited_user(
            username="single-use-invite",
            email="single-use-invite@example.com",
        )
        captured = {}
        with patch.object(
            NotificationService,
            "notify_account_invitation",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            InvitationService().issue(user)

        InvitationService().accept(captured["token"], INVITATION_TEST_PASSWORD)
        with pytest.raises(ValidationError):
            InvitationService().accept(captured["token"], "TlsCca!Invite-2026-Y8r4")

    def test_password_recovery_service_rejects_self_service_for_inactive_user(self):
        user = create_active_user(
            username="inactive-recovery",
            email="inactive-recovery@example.com",
        )
        user.is_active = False
        user.account_status = AccountStatus.PASSWORD_SET
        user.save(update_fields=["is_active", "account_status"])
        enable_totp(user)

        with pytest.raises(ValidationError):
            PasswordRecoveryService().issue(user)


    def test_totp_recovery_does_not_activate_account_without_password(self):
        user = UserFactory.create(
            username="totp-only-recovery",
            email="totp-only-recovery@example.com",
        )
        user.set_unusable_password()
        user.is_active = False
        user.account_status = AccountStatus.INVITED
        user.save(update_fields=["password", "is_active", "account_status"])

        setup = TwoFAService().setup(user)
        code = pyotp.TOTP(setup["secret"]).now()
        TwoFAService().verify_setup_token(setup["setup_token"], code)

        user.refresh_from_db()
        assert user.is_active is False
        assert user.account_status == AccountStatus.INVITED
        with pytest.raises(AuthenticationFailed):
            AuthenticationService().issue_tokens(user)
    def test_normal_login_requires_password_then_totp(self):
        user = create_active_user(
            username="two-factor-user",
            email="two-factor@example.com",
        )
        secret = enable_totp(user)
        client = APIClient()

        first = client.post(
            reverse("auth-login"),
            {"identifier": user.email, "password": ACTIVE_TEST_PASSWORD},
            format="json",
        )
        assert first.status_code == 200
        assert first.data["requires_2fa"] is True
        assert "access" not in first.data

        second = client.post(
            reverse("auth-2fa-verify"),
            {
                "challenge_token": first.data["challenge_token"],
                "code": pyotp.TOTP(secret).now(),
            },
            format="json",
        )
        assert second.status_code == 200
        assert second.data["access"]
        assert second.data["refresh"]

    def test_change_own_password_requires_totp(self):
        user = create_active_user(
            username="password-owner",
            email="password-owner@example.com",
            password="OldPassword123!",
        )
        secret = enable_totp(user)
        client = APIClient()
        client.force_authenticate(user=user)

        invalid = client.post(
            reverse("password-change-self"),
            {
                "old_password": "OldPassword123!",
                "new_password": "TlsCca!New-2026-Z4m8",
                "totp_code": "000000",
            },
            format="json",
        )
        assert invalid.status_code == 400

        valid = client.post(
            reverse("password-change-self"),
            {
                "old_password": "OldPassword123!",
                "new_password": "TlsCca!New-2026-Z4m8",
                "totp_code": pyotp.TOTP(secret).now(),
            },
            format="json",
        )
        assert valid.status_code == 200
        user.refresh_from_db()
        assert user.check_password("TlsCca!New-2026-Z4m8")

    def test_self_service_password_recovery_requires_email_link_and_totp(self):
        user = create_active_user(
            username="self-recovery",
            email="self-recovery@example.com",
            password="OldPassword123!",
        )
        secret = enable_totp(user)
        captured = {}

        with patch.object(
            NotificationService,
            "notify_password_reset_link",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            response = APIClient().post(
                reverse("auth-password-forgot"),
                {"email": user.email},
                format="json",
            )

        assert response.status_code == 200
        challenge = PasswordResetChallenge.objects.get(user=user)
        assert challenge.purpose == PasswordResetChallenge.SELF_SERVICE
        assert challenge.token_hash != captured["token"]

        client = APIClient()
        invalid = client.post(
            reverse("auth-password-reset"),
            {
                "token": captured["token"],
                "new_password": "TlsCca!New-2026-Z4m8",
                "totp_code": "000000",
            },
            format="json",
        )
        assert invalid.status_code == 400
        assert PasswordResetChallenge.objects.get(pk=challenge.pk).used_at is None

        valid = client.post(
            reverse("auth-password-reset"),
            {
                "token": captured["token"],
                "new_password": "TlsCca!New-2026-Z4m8",
                "totp_code": pyotp.TOTP(secret).now(),
            },
            format="json",
        )
        assert valid.status_code == 200
        assert "access" not in valid.data
        user.refresh_from_db()
        assert user.check_password("TlsCca!New-2026-Z4m8")
        assert PasswordResetChallenge.objects.get(pk=challenge.pk).used_at is not None

        reused = client.post(
            reverse("auth-password-reset"),
            {
                "token": captured["token"],
                "new_password": "TlsCca!Invite-2026-Y8r4",
                "totp_code": pyotp.TOTP(secret).now(),
            },
            format="json",
        )
        assert reused.status_code == 400

    def test_password_change_invalidates_pending_reset_links(self):
        user = create_active_user(
            username="password-reset-invalidated",
            email="password-reset-invalidated@example.com",
            password="OldPassword123!",
        )
        secret = enable_totp(user)
        captured = {}
        with patch.object(
            NotificationService,
            "notify_password_reset_link",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            response = APIClient().post(
                reverse("auth-password-forgot"),
                {"email": user.email},
                format="json",
            )
        assert response.status_code == 200

        client = APIClient()
        client.force_authenticate(user=user)
        changed = client.post(
            reverse("password-change-self"),
            {
                "old_password": "OldPassword123!",
                "new_password": "TlsCca!Changed-2026-P6v2",
                "totp_code": pyotp.TOTP(secret).now(),
            },
            format="json",
        )
        assert changed.status_code == 200

        with pytest.raises(ValidationError):
            PasswordRecoveryService().complete(
                captured["token"],
                "TlsCca!Invite-2026-Y8r4",
                totp_code=pyotp.TOTP(secret).now(),
            )

    def test_privileged_user_does_not_use_self_service_password_recovery(self):
        admin = create_active_user(
            username="privileged-recovery",
            email="privileged-recovery@example.com",
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=["is_staff", "is_superuser"])

        with patch.object(NotificationService, "notify_password_reset_link") as notify:
            response = APIClient().post(
                reverse("auth-password-forgot"),
                {"email": admin.email},
                format="json",
            )
        assert response.status_code == 200
        notify.assert_not_called()

    def test_rbac_privileged_user_does_not_use_self_service_password_recovery(self):
        admin = create_active_user(
            username="rbac-privileged-recovery",
            email="rbac-privileged-recovery@example.com",
        )
        grant_permission(admin, "user.security.reset_password")
        captured = {}

        with patch.object(
            NotificationService,
            "notify_password_reset_link",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ) as notify:
            response = APIClient().post(
                reverse("auth-password-forgot"),
                {"email": admin.email},
                format="json",
            )

        assert response.status_code == 200
        notify.assert_not_called()
        assert captured == {}

    def test_password_recovery_service_requires_admin_permission_for_admin_triggered_reset(self):
        actor = create_active_user(
            username="service-password-reset-denied",
            email="service-password-reset-denied@example.com",
        )
        target = create_active_user(
            username="service-password-reset-target",
            email="service-password-reset-target@example.com",
        )

        with pytest.raises(ValidationError):
            PasswordRecoveryService().issue(
                target,
                requested_by=actor,
                purpose=PasswordResetChallenge.ADMIN_TRIGGERED,
            )

    def test_twofa_recovery_service_requires_security_permission(self):
        actor = create_active_user(
            username="service-2fa-reset-denied",
            email="service-2fa-reset-denied@example.com",
        )
        target = create_active_user(
            username="service-2fa-reset-target",
            email="service-2fa-reset-target@example.com",
        )
        enable_totp(target)

        with pytest.raises(ValidationError):
            TwoFAService().reset_by_admin(target, actor=actor)

    def test_admin_triggered_password_reset_does_not_change_password(self):
        admin = create_active_user(
            username="password-admin",
            email="password-admin@example.com",
        )
        target = create_active_user(
            username="force-reset-target",
            email="force-reset@example.com",
            password="OldPassword123!",
        )
        grant_permission(admin, "user.security.reset_password")
        captured = {}
        client = APIClient()
        client.force_authenticate(user=admin)

        with patch.object(
            NotificationService,
            "notify_password_reset_link",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            response = client.post(
                reverse("password-force-reset", kwargs={"pk": target.pk}),
                format="json",
            )

        assert response.status_code == 202
        target.refresh_from_db()
        assert target.check_password("OldPassword123!")
        assert PasswordResetChallenge.objects.filter(
            user=target,
            purpose=PasswordResetChallenge.ADMIN_TRIGGERED,
            used_at__isnull=True,
        ).exists()
        assert captured["admin_triggered"] is True


@pytest.mark.django_db
class TestAdministrativeSecurityRecovery:
    def test_security_admin_can_reset_2fa_and_revoke_sessions(self):
        admin = create_active_user(
            username="security-admin",
            email="security-admin@example.com",
        )
        grant_permission(admin, "user.security.reset_2fa")
        target = create_active_user(
            username="reset-2fa-target",
            email="reset-2fa@example.com",
        )
        enable_totp(target)
        AuthenticationService().issue_tokens(target)
        captured = {}
        client = APIClient()
        client.force_authenticate(user=admin)

        with patch.object(
            NotificationService,
            "notify_twofa_reset",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            response = client.post(
                reverse("user-2fa-reset", kwargs={"pk": target.pk}),
                format="json",
            )

        assert response.status_code == 202
        target.refresh_from_db()
        profile = UserSecurityProfile.objects.get(user=target)
        assert profile.two_factor_enabled is False
        assert profile.totp_secret_encrypted is None
        assert target.is_active is False
        assert target.account_status == AccountStatus.PASSWORD_SET
        assert UserSession.objects.filter(user=target, revoked_at__isnull=False).exists()
        assert "token" in captured

    def test_admin_2fa_reset_invalidates_existing_self_service_reset(self):
        security_admin = create_active_user(
            username="security-reset-invalidates",
            email="security-reset-invalidates@example.com",
        )
        grant_permission(security_admin, "user.security.reset_2fa")
        target = create_active_user(
            username="security-reset-target",
            email="security-reset-target@example.com",
        )
        secret = enable_totp(target)
        captured = {}

        with patch.object(
            NotificationService,
            "notify_password_reset_link",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            reset_request = APIClient().post(
                reverse("auth-password-forgot"),
                {"email": target.email},
                format="json",
            )
        assert reset_request.status_code == 200

        client = APIClient()
        client.force_authenticate(user=security_admin)
        with patch.object(NotificationService, "notify_twofa_reset"):
            response = client.post(
                reverse("user-2fa-reset", kwargs={"pk": target.pk}),
                format="json",
            )
        assert response.status_code == 202

        with pytest.raises(ValidationError):
            PasswordRecoveryService().complete(
                captured["token"],
                "TlsCca!ShouldFail-2026-Q2w5",
                totp_code=pyotp.TOTP(secret).now(),
            )

    def test_user_admin_can_trigger_password_reset_but_not_2fa_reset(self):
        admin = create_active_user(
            username="user-admin",
            email="user-admin@example.com",
        )
        grant_permission(admin, "user.security.reset_password")
        target = create_active_user(
            username="user-admin-target",
            email="user-admin-target@example.com",
        )
        enable_totp(target)
        client = APIClient()
        client.force_authenticate(user=admin)

        with patch.object(NotificationService, "notify_password_reset_link"):
            password_response = client.post(
                reverse("password-force-reset", kwargs={"pk": target.pk}),
                format="json",
            )
        assert password_response.status_code == 202

        twofa_response = client.post(
            reverse("user-2fa-reset", kwargs={"pk": target.pk}),
            format="json",
        )
        assert twofa_response.status_code == 403

    def test_standard_role_cannot_trigger_security_recovery(self):
        user = create_active_user(
            username="commercial-user",
            email="commercial-user@example.com",
        )
        target = create_active_user(
            username="commercial-target",
            email="commercial-target@example.com",
        )
        grant_permission(user, "user.view")
        client = APIClient()
        client.force_authenticate(user=user)

        assert client.post(
            reverse("user-2fa-reset", kwargs={"pk": target.pk}),
            format="json",
        ).status_code == 403
        assert client.post(
            reverse("password-force-reset", kwargs={"pk": target.pk}),
            format="json",
        ).status_code == 403

    def test_lost_password_and_authenticator_can_be_recovered_by_two_admin_actions(self):
        security_admin = create_active_user(
            username="full-recovery-admin",
            email="full-recovery-admin@example.com",
        )
        grant_permission(security_admin, "user.security.reset_password")
        grant_permission(security_admin, "user.security.reset_2fa")
        target = create_active_user(
            username="full-recovery-target",
            email="full-recovery-target@example.com",
            password="OldPassword123!",
        )
        enable_totp(target)

        reset_capture = {}
        twofa_capture = {}
        client = APIClient()
        client.force_authenticate(user=security_admin)
        with patch.object(
            NotificationService,
            "notify_password_reset_link",
            side_effect=lambda **kwargs: reset_capture.update(kwargs),
        ):
            password_reset = client.post(
                reverse("password-force-reset", kwargs={"pk": target.pk}),
                format="json",
            )
        assert password_reset.status_code == 202

        with patch.object(
            NotificationService,
            "notify_twofa_reset",
            side_effect=lambda **kwargs: twofa_capture.update(kwargs),
        ):
            twofa_reset = client.post(
                reverse("user-2fa-reset", kwargs={"pk": target.pk}),
                format="json",
            )
        assert twofa_reset.status_code == 202
        assert reset_capture["admin_triggered"] is True
        assert twofa_capture["token"].count(".") == 1

        public = APIClient()
        reset_response = public.post(
            reverse("auth-password-reset"),
            {
                "token": reset_capture["token"],
                "new_password": "TlsCca!Recovered-2026-R9k3",
            },
            format="json",
        )
        assert reset_response.status_code == 200
        assert "access" not in reset_response.data

        setup_response = public.post(
            reverse("auth-2fa-recovery-setup"),
            {"setup_token": twofa_capture["token"]},
            format="json",
        )
        assert setup_response.status_code == 200
        recovery_code = pyotp.TOTP(setup_response.data["secret"]).now()

        verify_response = public.post(
            reverse("auth-2fa-recovery-verify"),
            {
                "setup_token": twofa_capture["token"],
                "code": recovery_code,
            },
            format="json",
        )
        assert verify_response.status_code == 200
        assert verify_response.data["access"]

        target.refresh_from_db()
        assert target.account_status == AccountStatus.ACTIVE
        assert target.is_active is True
        assert target.check_password("TlsCca!Recovered-2026-R9k3")
