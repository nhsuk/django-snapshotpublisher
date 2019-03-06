"""
.. module:: djangosnapshotpublisher.publisher_api
   :synopsis: PublisherAPI
"""

from datetime import datetime
import json

from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .lazy_encoder import LazyEncoder
from .models import ContentRelease, ReleaseDocument


API_TYPES = ['django', 'json']
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
ERROR_STATUS_CODE = {
    'content_release_already_exists': _('ContentRelease already exists'),
    'content_release_does_not_exist': _('ContentRelease doesn\'t exists'),
    'content_release_title_version_not_defined': _('Title or version need to be define'),
    'no_content_release_live': _('There is no live ContentRelease'),
    'wrong_datetime_format':  _('The datetime format is wrong, eg:2018-09-01T13:20:30+03:00'),
    'publishdatetime_in_past': _('Publish datetime must be in the future'),
    'base_content_release_does_not_exist': _('Base ContentRelease doesn\'t exists'),
    'content_release_publish': _('ContentRelease is published'),
    'content_release_not_publish': _('ContentRelease is not published'),
    'release_document_does_not_exist': _('ReleaseDocument doesn\'t exist'),
}


class PublisherAPI:
    """ PublisherAPI """

    def __init__(self, api_type='django'):
        if api_type not in API_TYPES:
            raise(_('Invalide type, only this api_types are available: {}'.format(
                ', '.join(API_TYPES))))
        self.api_type = api_type

    def send_response(self, status_code, data=None):
        """ send_response """
        if status_code == 'success':
            response = {
                'status': 'success',
            }
            if self.api_type == 'json':
                if isinstance(data, QuerySet):
                    data = [item.to_dict() for item in data]
                if isinstance(data, (ContentRelease, ReleaseDocument)):
                    data = data.to_dict()
            if data is not None:
                response['content'] = data
        else:
            response = {
                'status': 'error',
                'error_code': status_code,
                'error_msg': ERROR_STATUS_CODE[status_code],
            }
        if self.api_type == 'json':
            return json.dumps(response, cls=LazyEncoder)
        return response


    def add_content_release(self, site_code, title, version, based_on_release_uuid=None):
        """ add_content_release """
        try:
            ContentRelease.objects.get(
                site_code=site_code,
                title=title,
                version=version,
            )
            return self.send_response('content_release_already_exists')
        except ContentRelease.DoesNotExist:
            base_release = None
            if based_on_release_uuid is not None:
                try:
                    base_release = ContentRelease.objects.get(
                        site_code=site_code, uuid=based_on_release_uuid)
                except ContentRelease.DoesNotExist:
                    return self.send_response('base_content_release_does_not_exist')
            content_release = ContentRelease(
                site_code=site_code,
                title=title,
                version=version,
                base_release=base_release,
            )
            content_release.save()
            # TODO copy all children from base release to this release.
            return self.send_response('success', content_release)

    def remove_content_release(self, site_code, release_uuid):
        """ remove_content_release """
        try:
            ContentRelease.objects.get(site_code=site_code, uuid=release_uuid).delete()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def update_content_release(self, site_code, release_uuid, title=None, version=None):
        """ update_content_release """
        if not title and not version:
            return self.send_response('content_release_title_version_not_defined')
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            if title:
                content_release.title = title
            if version:
                content_release.version = version
            content_release.save()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def get_content_release_details(self, site_code, release_uuid):
        """ get_content_release_details """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            return self.send_response('success', content_release)
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def get_live_content_release(self, site_code):
        """ get_live_content_release """
        live_content_release = ContentRelease.objects.live(site_code)
        if live_content_release:
            return self.send_response('success', live_content_release)
        return self.send_response('no_content_release_live')

    def set_live_content_release(self, site_code, release_uuid):
        """ set_live_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            content_release.status = 1
            content_release.publish_datetime = timezone.now()
            content_release.save()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def freeze_content_release(self, site_code, release_uuid, publish_datetime):
        """ freeze_content_release """
        try:
            publish_datetime = datetime.strptime(publish_datetime, DATETIME_FORMAT)
            if publish_datetime < timezone.now():
                return self.send_response('publishdatetime_in_past')
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            content_release.status = 1
            content_release.publish_datetime = publish_datetime
            content_release.save()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
        except ValueError:
            return self.send_response('wrong_datetime_format')

    def unfreeze_content_release(self, site_code, release_uuid):
        """ unfreeze_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            if ContentRelease.objects.is_published(release_uuid):
                return self.send_response('content_release_publish')
            content_release.status = 0
            content_release.save()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def archive_content_release(self, site_code, release_uuid):
        """ archive_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            if not ContentRelease.objects.is_published(release_uuid):
                return self.send_response('content_release_not_publish')
            content_release.status = 2
            content_release.save()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def unarchive_content_release(self, site_code, release_uuid):
        """ unarchive_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            if not ContentRelease.objects.is_published(release_uuid):
                return self.send_response('content_release_not_publish')
            content_release.status = 1
            content_release.save()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def list_content_releases(self, site_code, status=None):
        """ list_content_releases """
        content_releases = ContentRelease.objects.filter(site_code=site_code)
        if status:
            content_releases = content_releases.filter(status=status)
        return self.send_response('success', content_releases)

    def get_document_from_content_release(
            self, site_code, release_uuid, document_key, content_type='content'):
        """get_document_from_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            release_document = ReleaseDocument.objects.get(
                content_release=content_release,
                document_key=document_key,
                content_type=content_type,
            )
            return self.send_response('success', release_document)
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
        except ReleaseDocument.DoesNotExist:
            return self.send_response('release_document_does_not_exist')

    def publish_document_to_content_release(
            self, site_code, release_uuid, document_json, document_key, content_type='content'):
        """ publish_document_to_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            release_document, created = ReleaseDocument.objects.update_or_create(
                content_release=content_release,
                document_key=document_key,
                defaults={
                    'document_json': document_json,
                    'content_type': content_type,
                },
            )
            return self.send_response('success', {'created': created})
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def unpublish_document_from_content_release(
            self, site_code, release_uuid, document_key, content_type='content'):
        """ unpublish_document_from_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            release_document = ReleaseDocument.objects.get(
                content_release=content_release,
                document_key=document_key,
                content_type=content_type,
            )
            release_document.delete()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
        except ReleaseDocument.DoesNotExist:
            return self.send_response('release_document_does_not_exist')
