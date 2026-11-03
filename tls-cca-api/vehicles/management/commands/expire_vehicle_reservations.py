"""Maintenance command for deterministic reservation expiration."""

from django.core.management.base import BaseCommand

from vehicles.services.reservation_services import expire_due_reservations


class Command(BaseCommand):
    help = "Expire due vehicle reservations and restore affected vehicles to stock."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of due reservations to process in this run.",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        if limit is not None and limit <= 0:
            self.stderr.write(self.style.ERROR("--limit must be a positive integer."))
            return 2

        count = expire_due_reservations(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(f"Expired {count} vehicle reservation(s).")
        )
        return 0
