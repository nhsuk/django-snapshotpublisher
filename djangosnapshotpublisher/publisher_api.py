import json

from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _

from .lazy_encoder import LazyEncoder
from .models import ContentRelease


API_TYPES = ['django', 'json']

ERROR_STATUS_CODE = {
    'content_release_already_exists': _('ContentRelease already exists'),
    'content_release_does_not_exist': _('ContentRelease doesn\'t exists'),
    'content_release_title_version_not_defined': _('Title or version need to be define'),
}

class PublisherAPI:

    def __init__(self, api_type='django'):
        if api_type not in API_TYPES:
            raise(_('Invalide type, only this api_types are available: {}'.format(', '.join(API_TYPES))))
        self.api_type = api_type

    def send_response(self, status_code, data=None):
        if status_code == 'success':
            response = {
                'status': 'success',
            }
            if self.api_type == 'json':
        #    if type(data) == dict:
        #         json.dumps(data)
        #     # if isinstance(data, QuerySet):
        #     #     pass
                if isinstance(data, (ContentRelease, ContentRelease)):
                    data = data.to_dict()
            if data:
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
        try:
            release = ContentRelease.objects.get(
                site_code=site_code,
                title=title,
                version=version,
            )
            return self.send_response('content_release_already_exists')
        except ContentRelease.DoesNotExist:
            base_release = None
            if based_on_release_uuid is not None:
                base_release = ContentRelease.objects.get(uuid=based_on_release_uuid)
            content_release = ContentRelease(
                site_code=site_code,
                title=title,
                version=version,
                base_release=base_release,
            )
            content_release.save()
            return self.send_response('success', content_release)

    def remove_content_release(self, site_code, release_uuid):
        try:
            ContentRelease.objects.get(uuid=release_uuid).delete()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
    
    def update_content_release(self, site_code, release_uuid, title=None, version=None):
        if not title and not version:
            return self.send_response('content_release_title_version_not_defined')
        try:
            content_release = ContentRelease.objects.get(uuid=release_uuid)
            if title:
                content_release.title = title
            if version:
                content_release.version = version
            content_release.save()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
 
    def get_content_release_details(self, site_code, release_uuid):
        try:
            content_release = ContentRelease.objects.get(uuid=release_uuid)
            return self.send_response('success', content_release)
        except:
            return self.send_response('content_release_does_not_exist')