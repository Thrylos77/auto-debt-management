"""Compatibility wrapper for the legacy 2FA module."""
from .twofa import Disable2FAView, Enable2FAView, VerifySetup2FAView
from .auth import VerifyTwoFALoginView

Login2FAView = VerifyTwoFALoginView
