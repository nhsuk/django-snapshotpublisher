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
    (0, 'PREVIEW'),
    (1, 'STAGED'),
    (2, 'LIVE'),
    (3, 'ARCHIVED'),
)

def valide_version(value):
    """ valide_version """
    match_version = re.match(r'^([0-9])+(\.[0-9]+)*$', value)
    if match_version:
        version_values = value.split('.')
        if all(v == '0' for v in version_values):
            raise ValidationError(
                _('%(value)s cannot only contain 0, e.g: 0.1'),
                code='version_none',
                params={'value': value},
            )
    else:
        raise ValidationError(
            _('%(value)s is not a correction, e.g: 2.1'),
            code='version_wrong_format',
            params={'value': value},
        )
    return True


class ReleaseDocumentExtraParameter(models.Model):
    """ ReleaseDocumentExtraParameter """
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
    """ ContentReleaseExtraParameter """
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
    version = models.CharField(max_length=20, blank=True, null=True,)
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
    is_stage = models.BooleanField(default=False)
    is_live = models.BooleanField(default=False)

    objects = ContentReleaseManager()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """ save """
        if self.version and self.status not in [2, 3] and valide_version(self.version):
            is_version_conflict = self.__class__.objects.filter(
                site_code=self.site_code,
                status__in=[1, 2, 3],
                version__gte=self.version,
            ).exclude(id=self.id)

            is_version_conflict = self.__class__.objects.filter(
                site_code=self.site_code,
                status__in=[1, 2, 3],
                version__gte=self.version,
            ).exclude(id=self.id).exists()

            if is_version_conflict:
                raise ValidationError(
                    _('Conflict version with staged, live or archived release(s), try bigger number'),
                    code='version_conflict_live_releases',
                )

        # NOTE: Validation now should only be performed on preview releases.
        if self.status == 0 and self.use_current_live_as_base_release and self.base_release:
            raise ValidationError(
                _('You cannot set a Base Release if you want to use the current live as the base\
                     release'),
                code='base_release_should_be_none',
            )

        if self.base_release and \
            (
                    self.base_release.status not in [2, 3] or \
                    (
                        self.base_release.publish_datetime and \
                            self.base_release.publish_datetime > timezone.now()
                    )
            ):
            raise ValidationError(
                _('Base release must to be live or archived'),
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
        instance_dict.pop('is_stage')
        instance_dict.pop('id')
        return instance_dict

    def copy_document_release_ref_from_baserelease(self):
        """ copy_document_release_ref_from_baserelease """
        if self.use_current_live_as_base_release:
            try:
                self.base_release = self.__class__.objects.get(
                    site_code=self.site_code,
                    is_live=True,
                    status=2,
                )
            except self.__class__.DoesNotExist:
                pass

        try:
            self.base_release = self.__class__.objects.get(is_live=True, status=2)
            for release_document in self.base_release.release_documents.all():
                try:
                    ReleaseDocument.objects.get(
                        document_key=release_document.document_key,
                        content_type=release_document.content_type,
                        content_releases=self,
                    )
                except ReleaseDocument.DoesNotExist:
                    try:
                        ReleaseDocumentExtraParameter.objects.get(
                            key='have_dynamic_elements',
                            content='True',
                            release_document=release_document,
                        )
                        new_release_document = ReleaseDocument.objects.get(pk=release_document.pk)
                        new_release_document.pk = None
                        new_release_document.save()
                        release_document_extra_parameters = ReleaseDocumentExtraParameter.objects.filter(
                            release_document=release_document,
                        )
                        for release_document_extra_parameter in release_document_extra_parameters:
                            new_release_document_extra_parameter = ReleaseDocumentExtraParameter.objects.get(pk=release_document_extra_parameter.pk)
                            new_release_document_extra_parameter.pk = None
                            new_release_document_extra_parameter.release_document = new_release_document
                            new_release_document_extra_parameter.save()
                        release_document_extra_parameter = ReleaseDocumentExtraParameter(
                            key='stage_dynamic_elements',
                            content='True',
                            release_document=release_document,
                        )
                        release_document_extra_parameter.save()
                        self.release_documents.add(new_release_document)
                    except ReleaseDocumentExtraParameter.DoesNotExist:
                        self.release_documents.add(release_document)
        except self.__class__.DoesNotExist:
            pass

        self.is_stage = True
        self.status = 1
        self.save()

    def remove_document_release_ref_from_baserelease(self):
        """ remove_document_release_ref_from_baserelease """
        if self.base_release:
            # remove document ref that exists in live release
            try:
                for release_document in self.base_release.release_documents.all():
                    try:
                        ReleaseDocument.objects.get(
                            document_key=release_document.document_key,
                            content_type=release_document.content_type,
                            content_releases=self,
                        )
                        self.release_documents.remove(release_document)
                    except ReleaseDocument.DoesNotExist:
                        pass
            except self.__class__.DoesNotExist:
                pass
        
            # remove document copy from live release
            dynamic_documents = self.release_documents.filter(
                parameters__key='stage_dynamic_elements',
                parameters__content='True',
            ).delete()

        self.base_release = None
        self.is_stage = False
        self.status = 0
        self.save()

    def copy(self, overide_data=None):
        """ copy """
        data = model_to_dict(self, exclude=['id', 'uuid', ])
        release_documents = data.pop('release_documents')

        # overide_data
        if overide_data and isinstance(overide_data, dict):
            data.update(overide_data)

        new_release = ContentRelease(**data)
        new_release.save()

        # release_documents
        for release_document in release_documents:
            new_release.release_documents.add(release_document)

        # extra_parameter
        extra_parameters = ContentReleaseExtraParameter.objects.filter(content_release=self)
        for extra_parameter in extra_parameters:
            extra_parameter_data = model_to_dict(extra_parameter, exclude=['id', 'content_release'])
            new_extra_parameter = ContentReleaseExtraParameter(**extra_parameter_data)
            new_extra_parameter.content_release = new_release
            new_extra_parameter.save()

        return new_release
