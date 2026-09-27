from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Compatibility wrapper around security-token cleanup."

    def handle(self, *args, **options):
        call_command("cleanup_security_tokens")
