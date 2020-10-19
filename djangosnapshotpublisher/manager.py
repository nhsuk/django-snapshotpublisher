"""
.. module:: djangosnapshotpublisher.manager
   :synopsis: djangosnapshotpublisher manager
"""
from django.db import models
from django.utils import timezone


class ContentReleaseManager(models.Manager):
    """ ContentReleaseManager """

    def stage(self, site_code):
        """ stage """
        return self.get_queryset().get(is_stage=True)

    #     self.model.copy_document_stage_releases(site_code)
    #     stage_content_release = self.get_queryset().filter(
    #         site_code=site_code,
    #         status=3,
    #         publish_datetime__lt=timezone.now(),
    #     ).order_by('-publish_datetime').first()
    #     return stage_content_release

    # def stages(self, site_code):
    #     """ stages """
    #     self.model.copy_document_stage_releases(site_code)
    #     return self.get_queryset().filter(
    #         site_code=site_code,
    #         status=3,
    #         publish_datetime__lt=timezone.now(),
    #     ).order_by('-publish_datetime')

    # def is_staged(self, uuid):
    #     """ is_published """
    #     return self.get_queryset().filter(
    #         uuid=uuid,
    #         publish_datetime__lt=timezone.now(),
            
    #     ).exists()

    def live(self, site_code):
        """ live """
        # current_live_release = None
        # try:
        #     current_live_release = self.get_queryset().get(
        #         site_code=site_code,
        #         status=2,
        #         is_live=True,
        #     )
        # except self.model.DoesNotExist:
        #     pass

        try:
            stage_content_release_ready = self.get_queryset().get(
                site_code=site_code,
                status=1,
                is_stage=True,
                publish_datetime__lt=timezone.now(),
            )
            stage_content_release_ready.is_live = True
            stage_content_release_ready.is_stage = False
            stage_content_release_ready.status = 2
            stage_content_release_ready.save()
            current_live_release = self.get_queryset().filter(
                site_code=site_code,
                status=2,
                is_live=True,
            )
            if current_live_release.exists():
                current_live_release.is_live = False
                current_live_release.status = 3
                current_live_release.save()
            current_live_release = stage_content_release_ready
        except self.model.DoesNotExist:
            pass

        return self.get_queryset().get(
            site_code=site_code,
            status=2,
            is_live=True,
        )


    def archived(self, site_code):
        """ archived """
        # self.model.copy_document_live_releases(site_code)
        return self.get_queryset().filter(
            site_code=site_code,
            status=3,
            is_live=False,
            is_stage=False,
        ).order_by('-publish_datetime')

        # check if stage to go live
        # self.model.copy_document_live_releases(site_code)
        # live_content_release = self.get_queryset().filter(
        #     site_code=site_code,
        #     status=1,
        #     publish_datetime__lt=timezone.now(),
        # ).order_by('-publish_datetime').first()
        # return live_content_release

    # def lives(self, site_code):
    #     """ lives """
    #     self.model.copy_document_live_releases(site_code)
    #     return self.get_queryset().filter(
    #         site_code=site_code,
    #         status=1,
    #         publish_datetime__lt=timezone.now(),
    #     ).order_by('-publish_datetime')

    # def is_published(self, uuid):
    #     """ is_published """
    #     return self.get_queryset().filter(
    #         uuid=uuid,
    #         publish_datetime__lt=timezone.now(),
    #     ).exists()
