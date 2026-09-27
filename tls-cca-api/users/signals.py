from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import UserPreference, UserSecurityProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_identity_profiles(sender, instance, created, **kwargs):
    if not created:
        return
    UserPreference.objects.get_or_create(user=instance)
    UserSecurityProfile.objects.get_or_create(
        user=instance,
        defaults={"last_password_change_at": timezone.now()},
    )
