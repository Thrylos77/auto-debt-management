import json
from django.dispatch import receiver
from simple_history.signals import pre_create_historical_record
from .models import User


# Signal to add roles snapshot to the historical record
# This will store the current roles of a User in the history record
@receiver(pre_create_historical_record)
def add_roles_snapshot(sender, **kwargs):
    instance = kwargs['instance']
    history_instance = kwargs['history_instance']
    if not isinstance(instance, User):
        return
    names = list(instance.roles.values_list('name', flat=True))
    data = json.loads(history_instance.history_change_reason or '{}')
    data['roles'] = names
    history_instance.history_change_reason = json.dumps(data)
