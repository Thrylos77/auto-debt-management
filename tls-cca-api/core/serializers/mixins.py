# core/serializers/mixins.py
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

class HistoricalChangesMixin(serializers.Serializer):
    """
    A serializer mixin for models using simple-history.
    It adds fields for history metadata and a 'changes' field
    to show what was modified in an update.
    """
    history_user = serializers.StringRelatedField(read_only=True)
    history_type_display = serializers.CharField(source='get_history_type_display', read_only=True)
    changes = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DictField())
    def get_changes(self, obj):
        """
        Return the modified fields and their old/new values
        for objects with a change type of '~' (modification).
        """
        if obj.history_type != '~' or not hasattr(obj, 'prev_record'):
            return None

        delta = obj.diff_against(obj.prev_record)
        changes = {}
        for change in delta.changes:
            changes[change.field] = {
                "old": change.old,
                "new": change.new
            }
        return changes