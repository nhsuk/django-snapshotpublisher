"""
.. module:: djangosnapshotpublisher.manager
   :synopsis: djangosnapshotpublisher manager
"""
from django.db import models
from django.utils import timezone


class ContentReleaseManager(models.Manager):
    """ ContentReleaseManager """

    def live(self, site_code):
        """ live """
        self.model.copy_document_live_releases(site_code)
        live_content_release = self.get_queryset().filter(
            site_code=site_code,
            status=1,
            publish_datetime__lt=timezone.now(),
        ).order_by('-publish_datetime').first()
        return live_content_release

    def lives(self, site_code):
        """ lives """
        self.model.copy_document_live_releases(site_code)
        return self.get_queryset().filter(
            site_code=site_code,
            status=1,
            publish_datetime__lt=timezone.now(),
        )

    def is_published(self, uuid):
        """ is_published """
        return self.get_queryset().filter(
            uuid=uuid,
            publish_datetime__lt=timezone.now(),
         ).exists()
