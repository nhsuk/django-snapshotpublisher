"""
.. module:: djangosnapshotpublisher.models
"""

import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .manager import ContentReleaseManager


CONTENT_RELEASE_STATUS = (
    (0, 'PENDING'),
    (1, 'FROZEN'),
    (2, 'ARCHIVED'),
)

def valide_version(value):
    """ valide_version """
    valid = True
    match_version = re.match(r'^([0-9])+(\.[0-9]+)*$', value)
    if match_version:
        version_values = value.split('.')
        if all(v == '0' for v in version_values):
            raise ValidationError(
                _('%(value)s cannot only contain 0, e.g: 0.1'),
                code='version_none',
                params={'value': value},
            )
            valid = False
    else:
        raise ValidationError(
            _('%(value)s is not a correction, e.g: 2.1'),
            code='version_wrong_format',
            params={'value': value},
        )
        valid = False

    return valid


class ReleaseDocumentExtraParameter(models.Model):
    key = models.SlugField(max_length=255)
    content = models.TextField(null=True)
    release_document = models.ForeignKey(
        'ReleaseDocument',
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name='parameters',
    )

    def to_dict(self):
        """ to_dict """
        instance_dict = model_to_dict(self)
        instance_dict['release_document_uuid'] = self.release_document.uuid
        instance_dict.pop('release_document')
        instance_dict.pop('id')
        return instance_dict


class ReleaseDocument(models.Model):
    """ ReleaseDocument """
    document_key = models.CharField(max_length=250)
    content_type = models.CharField(max_length=100, default='content')
    document_json = models.TextField(null=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return '{} - {}'.format(self.content_type, self.document_key)

    def to_dict(self):
        """ to_dict """
        instance_dict = model_to_dict(self)
        instance_dict.pop('id')
        return instance_dict


class ContentReleaseExtraParameter(models.Model):
    key = models.SlugField(max_length=255)
    content = models.TextField(null=True)
    content_release = models.ForeignKey(
        'ContentRelease',
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name='parameters',
    )

    def to_dict(self):
        """ to_dict """
        instance_dict = model_to_dict(self)
        instance_dict['content_release_uuid'] = self.content_release.uuid
        instance_dict.pop('content_release')
        instance_dict.pop('id')
        return instance_dict


class ContentRelease(models.Model):
    """ ContentRelease """
    uuid = models.UUIDField(max_length=255, unique=True, default=uuid.uuid4)
    version = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=100)
    site_code = models.SlugField(max_length=100)
    status = models.IntegerField(choices=CONTENT_RELEASE_STATUS, default=0)
    publish_datetime = models.DateTimeField(blank=True, null=True,)
    use_current_live_as_base_release = models.BooleanField(default=False)
    base_release = models.ForeignKey(
        'ContentRelease',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    release_documents = models.ManyToManyField(
        ReleaseDocument,
        blank=True,
        related_name='content_releases'
    )
    is_live = models.BooleanField(default=False)

    objects = ContentReleaseManager()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """ save """
        if valide_version(self.version):
            is_version_conflict_with_live = self.__class__.objects.filter(
                site_code=self.site_code,
                status__in=[1, 2],
                version__gte=self.version,
            ).exclude(id=self.id).exists()

            if not self.is_live and is_version_conflict_with_live:
                raise ValidationError(
                    _('Conflict version with frozen or archived release(s), try bigger number'),
                    code='version_conflict_live_releases',
                )
        
        if self.use_current_live_as_base_release and self.base_release:
            raise ValidationError(
                _('You cannot set a Base Release if you want to use the current live as the base\
                     release'),
                code='base_release_should_be_none',
            )

        if self.base_release and self.base_release.status != 1 and \
                self.base_release.publish_datetime and \
                self.base_release.publish_datetime < timezone.now():
            raise ValidationError(
                _('Base release must to be live'),
                code='base_release_should_be_none',
            )

        super(ContentRelease, self).save(*args, **kwargs)

    def to_dict(self):
        """ to_dict """
        instance_dict = model_to_dict(self)
        instance_dict['uuid'] = self.uuid
        instance_dict['status'] = self.get_status_display()
        instance_dict.pop('release_documents')
        instance_dict.pop('is_live')
        instance_dict.pop('id')
        return instance_dict

    @classmethod
    def copy_document_live_releases(cls, site_code):
        live_content_release_not_ready = cls.objects.filter(
            site_code=site_code,
            status=1,
            publish_datetime__lt=timezone.now(),
            is_live=False,
        ).order_by('publish_datetime')

        for content_release in live_content_release_not_ready:
            content_release.copy_document_release_ref_from_baserelease()
    
    def copy_document_release_ref_from_baserelease(self):
        base_release = self.base_release
        if self.use_current_live_as_base_release:
            base_release = self.__class__.objects.filter(
                publish_datetime__lt=self.publish_datetime, site_code=self.site_code).order_by(
                    '-publish_datetime').first()

        if base_release:
            for release_document in base_release.release_documents.all():
                try:
                    ReleaseDocument.objects.get(
                        document_key=release_document.document_key,
                        content_type=release_document.content_type,
                        content_releases=self,
                    )
                except ReleaseDocument.DoesNotExist:
                    self.release_documents.add(release_document)
        self.is_live = True
        self.save()
