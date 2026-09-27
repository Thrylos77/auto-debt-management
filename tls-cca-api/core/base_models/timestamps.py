from django.db import models


class TimeStampedModel(models.Model):
    """Reusable timestamp fields for platform/domain models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
