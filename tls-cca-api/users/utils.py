import re
import secrets
import string

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


def generate_otp(length=6):
    return "".join(secrets.choice(string.digits) for _ in range(length))


class RegexPasswordValidator:
    def __init__(self, pattern=None, message=None):
        if not pattern:
            raise ValueError("A regex pattern must be provided.")
        self.pattern = re.compile(pattern)
        self.message = message or _("This password does not meet the required pattern.")

    def validate(self, password, user=None):
        if not self.pattern.search(password):
            raise ValidationError(self.message, code="password_no_match")

    def get_help_text(self):
        return self.message
