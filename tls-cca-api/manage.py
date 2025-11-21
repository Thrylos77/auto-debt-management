#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Automatic admin and RBAC creation when running the server with DEBUG=True
    if 'runserver' in sys.argv:
        import django
        django.setup()
        from django.conf import settings
        if getattr(settings, 'DEBUG', False) and os.environ.get('RUN_MAIN') == 'true':
            from django.core.management import call_command
            call_command('init_admin')
            call_command('seed_rbac_v2')

    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()