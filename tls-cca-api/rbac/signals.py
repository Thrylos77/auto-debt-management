import json
from django.dispatch import receiver
from django.db.models.signals import m2m_changed
from .models import Role


@receiver(m2m_changed, sender=Role.permissions.through)
def save_permissions_in_role_history(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        # The 'instance' is the Role object whose permissions were changed.
        
        # Get the most recent historical record for this role.
        # For a new role, this will be the '+' record created just before.
        # For an updated role, this will be the '~' record.
        latest_history = instance.history.first()
        if not latest_history:
            return

        # Get the current, up-to-date list of permission codes.
        current_permission_codes = list(instance.permissions.values_list('code', flat=True))
        # Safely load any existing data from history_change_reason.
        try:
            data = json.loads(latest_history.history_change_reason or '{}')
        except (json.JSONDecodeError, TypeError):
            data = {}
        # Update the permissions snapshot and save it back as JSON.
        data['permissions'] = current_permission_codes
        latest_history.history_change_reason = json.dumps(data)
        latest_history.save(update_fields=['history_change_reason'])
