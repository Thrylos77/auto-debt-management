""" Users Models """
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from simple_history.models import HistoricalRecords
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.utils.validators import phone_validator

class User(AbstractUser):
    # AbstractUser provides: id, username, first_name, last_name, email, password, etc.
    # We only need to add our custom fields.
    # We override the email field to make it unique, as it's not by default in AbstractUser.
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=30, blank=True, validators=[phone_validator])
    address = models.TextField(blank=True)
    birthday = models.DateField(blank=True, null=True)
    roles = models.ManyToManyField('rbac.Role', related_name='users', blank=True)
    groups = models.ManyToManyField('rbac.Group', related_name='users', blank=True)

    history = HistoricalRecords(excluded_fields=['last_login'])
    
    # The default REQUIRED_FIELDS for AbstractUser is ['email'].
    # We are keeping it and adding first_name and last_name. The USERNAME_FIELD ('username')
    # and password are required by default for createsuperuser.
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    @property
    def all_permissions(self):
        from rbac.services import permission_services
        return permission_services.get_user_permissions(self)
    
    def has_permission(self, code: str) -> bool:
        return self.all_permissions.filter(code=code).exists()
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} {self.username}"

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    EXPIRATION_MINUTES = 5

    def is_valid(self):
        # OTP is valid for 5 minutes
        expiration_time = self.created_at + timedelta(minutes=self.EXPIRATION_MINUTES)
        return timezone.now() < expiration_time and not self.is_used

    class Meta:
        verbose_name = "Password Reset OTP"
        verbose_name_plural = "Password Reset OTPs"
        ordering = ['-created_at']
            
    def __str__(self):
        return f"OTP for {self.user} created at {self.created_at}"