from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

class Command(BaseCommand):
    help = 'Deletes all expired tokens from the blacklist.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Flushing expired tokens...'))
        
        expired_tokens = BlacklistedToken.objects.filter(token__expires_at__lt=timezone.now())
        count = expired_tokens.count()
        expired_tokens.delete()
        
        self.stdout.write(self.style.SUCCESS(f'✔️  Successfully flushed {count} expired tokens.'))