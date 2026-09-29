"""Sensitive-operation throttles."""

from rest_framework.throttling import SimpleRateThrottle


class IPRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginRateThrottle(IPRateThrottle):
    scope = "login"


class TwoFARateThrottle(IPRateThrottle):
    scope = "twofa"


class PasswordResetRateThrottle(IPRateThrottle):
    scope = "password_reset"
