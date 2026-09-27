"""Copy legacy Core settings into the new Configuration app."""

from django.core.management.base import BaseCommand
from django.db import connection

from configuration.models import SystemSetting
from configuration.registry import get_setting_definition
from configuration.services.type_codec import ConfigurationTypeCodec


LEGACY_TABLE = "core_systemsetting"


class Command(BaseCommand):
    help = "Copy legacy core_systemsetting rows into configuration_systemsetting."

    def handle(self, *args, **options):
        table_names = connection.introspection.table_names()
        if LEGACY_TABLE not in table_names:
            self.stdout.write(
                self.style.WARNING(
                    "No legacy core_systemsetting table found; nothing to migrate."
                )
            )
            return

        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT "key", "value" FROM "{LEGACY_TABLE}" ORDER BY "key"'
            )
            rows = cursor.fetchall()

        migrated = 0
        skipped = 0

        for key, raw_value in rows:
            definition = get_setting_definition(key)
            if definition is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping unregistered legacy setting: {key}"
                    )
                )
                skipped += 1
                continue

            try:
                typed_value = ConfigurationTypeCodec.decode(
                    raw_value,
                    definition.value_type,
                )
                encoded_value = ConfigurationTypeCodec.encode(
                    typed_value,
                    definition.value_type,
                )
            except ValueError as exc:
                self.stdout.write(
                    self.style.ERROR(
                        f"Skipping invalid setting {key}: {exc}"
                    )
                )
                skipped += 1
                continue

            SystemSetting.objects.update_or_create(
                key=definition.key,
                scope=definition.scope,
                scope_ref="",
                defaults={
                    "category": definition.category,
                    "value": encoded_value,
                    "description": definition.description,
                    "value_type": definition.value_type,
                    "is_public": definition.is_public,
                },
            )
            migrated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Legacy settings migrated: {migrated}; skipped: {skipped}."
            )
        )
