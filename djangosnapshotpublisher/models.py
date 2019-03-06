import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _

from .manager import ContentReleaseManager, ReleaseDocumentManager


CONTENT_RELEASE_STATUS = (
    (0, 'PENDING'),
    (1, 'FROZEN'),
    (2, 'ARCHIVED'),
)

def valide_version(value):
    valid = True
    match_version = re.match( r'^([0-9])+(\.[0-9]+)*$',value)
    if match_version:
        version_values = value.split('.')
        if all(v == '0' for v in version_values):
            raise ValidationError(
                _('%(value)s cannot only contain 0, e.g: 0.1'), code='version_none',
                params={'value': value},
            )
            valid = False
    else:
        raise ValidationError(
            _('%(value)s is not a correction, e.g: 2.1'), code='version_wrong_format',
            params={'value': value},
        )
        valid = False
    
    return valid


class ContentRelease(models.Model):
    uuid = models.UUIDField(max_length=255, unique=True, default=uuid.uuid4, editable=False)
    version = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=100)
    site_code = models.SlugField(max_length=100)
    status = models.IntegerField(choices=CONTENT_RELEASE_STATUS, default=0)
    publish_datetime = models.DateTimeField(blank=True, null=True,)
    base_release = models.ForeignKey(
        'ContentRelease',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    objects = ContentReleaseManager()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if valide_version(self.version):
            is_version_conflict_with_live = self.__class__.objects.filter(
                site_code=self.site_code,
                status__in=[1, 2],
                version__gte=self.version,
            ).exclude(id=self.id).exists()

            if is_version_conflict_with_live:
                raise ValidationError(
                    _('Conflict version with frozen or archived release(s), try bigger number'), code='version_conflict_live_releases',
                )
        super(ContentRelease, self).save(*args, **kwargs)

    def to_dict(self):
        instance_dict = model_to_dict(self)
        instance_dict['uuid'] = self.uuid
        instance_dict['status'] = self.get_status_display()
        return instance_dict


class ReleaseDocument(models.Model):
    document_key = models.SlugField(max_length=100, unique=True)
    content_release = models.ForeignKey(
        'ContentRelease',
        blank=False,
        null=False,
        on_delete=models.CASCADE,
    )
    content_type = models.SlugField(max_length=100, default='content')
    document_json = models.TextField(null=True)
    objects = ReleaseDocumentManager()

    class Meta:
        unique_together = (('document_key', 'content_release'),)

    def to_dict(self):
        instance_dict = model_to_dict(self)
        instance_dict['content_release_uuid'] = self.content_release.uuid
        del(instance_dict['content_release'])
        return instance_dict