"""Identity model for application users."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from core.utils.validators import phone_validator


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(max_length=30, blank=True, validators=[phone_validator])
    address = models.TextField(blank=True)
    birthday = models.DateField(blank=True, null=True)

    history = HistoricalRecords(
        excluded_fields=["last_login"],
        history_change_reason_field=models.TextField(null=True),
    )

    REQUIRED_FIELDS = ["first_name", "last_name", "email"]

    def __str__(self):
        return f"{self.get_full_name()} {self.username}".strip()
