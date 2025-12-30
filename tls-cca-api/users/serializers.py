# This file is responsible for:
# - Validating incoming data (e.g., from forms or API requests)
# - Transforming Python/Django objects (models) to and from JSON
# - Defining the structure of data exposed or expected by the API
import json
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from django.contrib.auth.password_validation import validate_password
from .services import user_services
from rbac.models import Group, Role
from drf_spectacular.utils import extend_schema_field

# Show the User model without exposing the password field
class UserSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all())
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all())

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'phone', 'birthday', 'address', 'roles', 'groups')
# Serializer for user registration
class RegisterSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all(), required=False)
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all(), required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'birthday', 'address', 'email', 'phone',  'roles', 'groups', 'password']
        read_only_fields = ['id']
        extra_kwargs = {'password': {'write_only': True}}


    def validate_password(self, value):
        validate_password(value)
        return value
    
    def create(self, validated_data):
        return user_services.create_user(validated_data)


# --- Password Change Serializers ---
class ChangeOwnPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        user = self.context['request'].user
        # We call Django's validator here, but the main logic is in the service
        validate_password(value, user=user)
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        return user_services.change_user_password(
            user=user,
            old_password=self.validated_data['old_password'],
            new_password=self.validated_data['new_password']
        )


class AdminChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        user = self.context.get("target_user")
        validate_password(value, user=user)
        return value
    
    def update(self, instance, validated_data):
        return user_services.change_user_password(
            user=instance,
            new_password=validated_data["new_password"]
        )

# -- Serializer for the OTP used in password reset --
class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("⚠️ User not found.")
        self.context['user'] = user
        return value

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)

    def validate(self, data):
        try:
            user = User.objects.get(email=data['email'])
            self.context['user'] = user
            # The core OTP validation logic is in the service
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})
        return data


# Serializer for the logout endpoint to ensure refresh token is provided
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    default_error_messages = {
        'bad_token': ('Token is invalid or expired')
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except Exception:
            self.fail('bad_token')



# Serializer for the historical records of the User model
class HistoricalUserSerializer(serializers.ModelSerializer):
    # The user who made the change, represented by their username for clarity.
    history_user = serializers.StringRelatedField()
    # Add a human-readable field for the history type (+, ~, -)
    history_type_display = serializers.CharField(source='get_history_type_display', read_only=True)
    changes = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display',
            'history_user', 'changes', 'username', 'email',
            'last_name', 'roles', 'is_active'
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, obj):
        if not obj.history_change_reason:
            return []
        try:
            data = json.loads(obj.history_change_reason)
            return data.get('roles', [])
        except (json.JSONDecodeError, TypeError):
            return []
        
    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_changes(self, obj):
        if obj.history_type == '~' and obj.prev_record:
            delta = obj.diff_against(obj.prev_record)
            changes_list = []
            for change in delta.changes:
                if change.field == 'date_joined':
                    continue
                # For security, we never show old or new password values.
                elif change.field == 'password':
                    changes_list.append({'field': 'password', 'old': '********', 'new': '********'})
                else:
                    changes_list.append({'field': change.field, 'old': change.old, 'new': change.new})
            return changes_list
        return None