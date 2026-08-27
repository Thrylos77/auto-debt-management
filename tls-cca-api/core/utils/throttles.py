"""
Custom throttles for rate-limiting sensitive endpoints.
"""
from rest_framework.throttling import SimpleRateThrottle


class OTPRateThrottle(SimpleRateThrottle):
    """
    Limits OTP requests (request & reset) to 3 per hour per user.
    """
    scope = 'otp'

    def get_cache_key(self, request, view):
        # Use user ID if authenticated, otherwise fallback to IP
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class LoginRateThrottle(SimpleRateThrottle):
    """
    Limits login attempts to 5 per minute per IP.
    """
    scope = 'login'

    def get_cache_key(self, request, view):
        # Throttle by IP since user is not authenticated yet at login
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}
