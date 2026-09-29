"""JWT authentication with mandatory MFA enforcement."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from users.models import AccountStatus, UserSecurityProfile


class EnforcedJWTAuthentication(JWTAuthentication):
    """Reject sessions for accounts that have not completed MFA enrollment."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, token = result
        profile = UserSecurityProfile.objects.filter(user=user).first()
        if (
            not user.is_active
            or user.account_status != AccountStatus.ACTIVE
            or not profile
            or not profile.two_factor_enabled
            or not profile.totp_secret_encrypted
            or not user.has_usable_password()
        ):
            raise AuthenticationFailed("Account onboarding is not complete.")

        return user, token


class EnforcedJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Expose the enforced JWT authentication scheme in OpenAPI."""

    target_class = "users.authentication.EnforcedJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object(
            header_name="Authorization",
            token_prefix="Bearer",
            bearer_format="JWT",
        )
