from django.db import models
from django.utils import timezone


class ContentReleaseManager(models.Manager):

    def live(self, site_code):
        return self.get_queryset().filter(
                site_code=site_code,
                status=1,
                publish_datetime__lt=timezone.now(),
            ).order_by('-publish_datetime').first()

    def lives(self, site_code):
        return self.get_queryset().filter(
                site_code=site_code,
                status=1,
                publish_datetime__lt=timezone.now(),
            )

    def is_published(self, uuid):
        return self.get_queryset().filter(
                uuid=uuid,
                publish_datetime__lt=timezone.now(),
            ).exists()