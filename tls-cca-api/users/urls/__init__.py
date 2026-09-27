"""Canonical Users URL tree.

The three child modules remain independently readable, while this package is

the only module imported by ``config.v1_urls`` for the Users surface.
"""

from .account import urlpatterns as account_urlpatterns
from .auth import urlpatterns as auth_urlpatterns
from .security import urlpatterns as security_urlpatterns


urlpatterns = [
    *auth_urlpatterns,
    *account_urlpatterns,
    *security_urlpatterns,
]

__all__ = ["urlpatterns"]
