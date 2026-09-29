from importlib import import_module
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_users_modules_have_cohesive_merged_boundaries():
    expected_modules = {
        "users.models.security",
        "users.serializers.account",
        "users.serializers.auth",
        "users.services.authentication",
        "users.services.invitation_service",
        "users.services.password_recovery_service",
        "users.services.password_service",
        "users.services.session_service",
        "users.services.twofa_service",
        "users.services.user_service",
        "users.security_utils",
        "users.utils",
        "users.rbac_registry",
        "users.signals",
        "users.views.auth",
        "users.views.onboarding",
        "users.views.passwords",
        "users.views.sessions",
        "users.views.twofa",
        "users.views.users",
    }

    for module_name in expected_modules:
        import_module(module_name)

    assert not (PROJECT_ROOT / "users/models/twofa.py").exists()
    assert not (PROJECT_ROOT / "users/serializers/twofa.py").exists()
    assert not (PROJECT_ROOT / "users/serializers/preferences.py").exists()
    assert not (PROJECT_ROOT / "users/serializers/sessions.py").exists()
    assert not (PROJECT_ROOT / "users/serializers/invitations.py").exists()
    assert not (PROJECT_ROOT / "users/views/preferences.py").exists()
    assert not (PROJECT_ROOT / "users/views/security_admin.py").exists()
    assert not (PROJECT_ROOT / "users/services/token_service.py").exists()


def test_merged_serializers_expose_all_expected_public_classes():
    account = import_module("users.serializers.account")
    auth = import_module("users.serializers.auth")
    views_users = import_module("users.views.users")

    for name in (
        "UserPreferenceSerializer",
        "UserSessionSerializer",
        "Enable2FASerializer",
        "VerifySetup2FASerializer",
        "SessionActionResponseSerializer",
    ):
        assert hasattr(account, name)

    assert (
        account.SessionActionResponseSerializer.__module__
        == "users.serializers.account"
    )
    for name in ("UserPreferenceSerializer", "UserPreference"):
        assert hasattr(views_users, name)

    for name in (
        "LoginSerializer",
        "Login2FASerializer",
        "LogoutSerializer",
        "AcceptInvitationSerializer",
        "VerifyInvitationTwoFASerializer",
        "TwoFARecoverySetupSerializer",
        "TwoFARecoveryVerifySerializer",
    ):
        assert hasattr(auth, name)


def test_all_users_runtime_modules_import_cleanly():
    runtime_modules = (
        "users.admin",
        "users.authentication",
        "users.models",
        "users.models.invitations",
        "users.models.preferences",
        "users.models.security",
        "users.models.sessions",
        "users.models.user",
        "users.serializers",
        "users.serializers.account",
        "users.serializers.auth",
        "users.serializers.passwords",
        "users.serializers.users",
        "users.services",
        "users.policies",
        "users.views",
        "users.urls",
        "users.urls.auth",
        "users.urls.account",
        "users.urls.security",
        "users.management.commands.cleanup_security_tokens",
        "users.management.commands.init_admin",
    )

    for module_name in runtime_modules:
        import_module(module_name)
