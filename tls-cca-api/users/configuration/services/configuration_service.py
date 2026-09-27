"""Application service for typed system configuration."""

from django.core.exceptions import ValidationError
from django.db import transaction

from audit.services import AuditService

from configuration.models import SystemSetting
from configuration.registry import get_setting_definition
from .type_codec import ConfigurationTypeCodec


SENSITIVE_KEYWORDS = (
    "password",
    "secret",
    "token",
    "private_key",
    "authorization",
    "cookie",
    "otp",
)


class ConfigurationService:
    """Read and write registered, non-secret application settings."""

    @classmethod
    def get_definition_or_raise(cls, key: str):
        definition = get_setting_definition(key)
        if definition is None:
            raise ValidationError(
                {"key": f"Unknown configuration key: {key}."}
            )
        return definition

    @classmethod
    def get(cls, key: str, default=None):
        """Return a typed value, falling back to the registry default."""

        definition = get_setting_definition(key)
        if definition is None:
            if default is not None:
                return default
            return None

        setting = SystemSetting.objects.filter(
            key=key,
            scope=definition.scope,
            scope_ref="",
        ).first()

        if setting is None:
            if default is not None:
                return default
            return definition.default

        try:
            return ConfigurationTypeCodec.decode(
                setting.value,
                setting.value_type,
            )
        except ValueError as exc:
            raise ValidationError({key: str(exc)}) from exc

    @classmethod
    def get_record(cls, key: str):
        definition = cls.get_definition_or_raise(key)
        return SystemSetting.objects.filter(
            key=key,
            scope=definition.scope,
            scope_ref="",
        ).first()

    @classmethod
    @transaction.atomic
    def set(
        cls,
        key: str,
        value,
        *,
        actor=None,
        request=None,
        description=None,
        is_public=None,
    ):
        """Validate, persist and audit one registered configuration key."""

        definition = cls.get_definition_or_raise(key)

        if any(keyword in key.lower() for keyword in SENSITIVE_KEYWORDS):
            raise ValidationError(
                {
                    "key": (
                        "Sensitive secrets must remain in environment "
                        "configuration."
                    )
                }
            )

        try:
            encoded_value = ConfigurationTypeCodec.encode(
                value,
                definition.value_type,
            )
            typed_value = ConfigurationTypeCodec.decode(
                encoded_value,
                definition.value_type,
            )
        except ValueError as exc:
            raise ValidationError({"value": str(exc)}) from exc

        if definition.validator is not None:
            try:
                definition.validator(typed_value)
            except ValueError as exc:
                raise ValidationError({"value": str(exc)}) from exc

        setting = SystemSetting.objects.filter(
            key=definition.key,
            scope=definition.scope,
            scope_ref="",
        ).first()
        created = setting is None

        if created:
            # Registry metadata is authoritative when a setting is first created.
            setting = SystemSetting.objects.create(
                key=definition.key,
                category=definition.category,
                value=encoded_value,
                description=(
                    definition.description
                    if description is None
                    else description
                ),
                value_type=definition.value_type,
                is_public=(
                    definition.is_public
                    if is_public is None
                    else bool(is_public)
                ),
                scope=definition.scope,
                scope_ref="",
                updated_by=(
                    actor
                    if getattr(actor, "pk", None)
                    else None
                ),
            )
        else:
            # Optional metadata fields are only changed when explicitly supplied.
            # This prevents a normal value update from silently resetting metadata.
            setting.category = definition.category
            setting.value = encoded_value
            setting.value_type = definition.value_type

            if description is not None:
                setting.description = description

            if is_public is not None:
                setting.is_public = bool(is_public)

            if getattr(actor, "pk", None):
                setting.updated_by = actor
            setting.save(
                update_fields=[
                    "category",
                    "value",
                    "value_type",
                    "description",
                    "is_public",
                    "updated_by",
                    "updated_at",
                ]
            )

        # Only whitelisted metadata is included. The actual configuration value
        # is deliberately excluded from audit records, even for non-secret keys.
        # Keep the audit event inside the same transaction as the setting update.
        # This makes the configuration change and its audit trail succeed or roll
        # back together, while also keeping the event immediately queryable.
        AuditService.record(
            actor=actor,
            category="ADMINISTRATION",
            action="configuration.set",
            resource=setting,
            status="success",
            request=request,
            metadata={
                "key": definition.key,
                "created": created,
                "value_type": definition.value_type,
            },
        )
        return setting

    @classmethod
    def list_settings(cls, *, public_only=False):
        """Return persisted settings ordered for deterministic API output."""

        queryset = SystemSetting.objects.all().order_by("category", "key")
        if public_only:
            queryset = queryset.filter(is_public=True)
        return queryset
