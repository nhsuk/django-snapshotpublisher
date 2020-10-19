"""
.. module:: djangosnapshotpublisher.publisher_api
   :synopsis: PublisherAPI
"""

from datetime import datetime
from functools import reduce
from operator import itemgetter
import json

from django.db.models import CharField, Case, Q, Count, When, Value as V
from django.db.models.functions import Concat
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .lazy_encoder import LazyEncoder
from .models import (ContentRelease, ReleaseDocumentExtraParameter, ReleaseDocument,
                     ContentReleaseExtraParameter)


API_TYPES = ['django', 'json']
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
ERROR_STATUS_CODE = {
    'wrong_api_type': _('Invalide type, only this api_types are available: {}'.format(
        ', '.join(API_TYPES))),
    'content_release_already_exists': _('ContentRelease already exists'),
    'content_release_does_not_exist': _('ContentRelease doesn\'t exists'),
    'content_release_title_version_not_defined': _('Title or version need to be define'),
    'no_content_release_live': _('There is no live ContentRelease'),
    'not_datetime':  _('Invalid datetime passed'),
    'publishdatetime_in_past': _('Publish datetime must be in the future'),
    'base_content_release_does_not_exist': _('Base ContentRelease doesn\'t exists'),
    'content_release_publish': _('ContentRelease is published'),
    'content_release_not_publish': _('ContentRelease is not published'),
    'release_document_does_not_exist': _('ReleaseDocument doesn\'t exist'),
    'parameters_missing': _('Parameter(s) missing'),
    'content_release_more_than_one': _('More than One Content Release'),
    'content_release_extra_parameter_does_not_exist': _(
        'ContentReleaseExtraParameter doesn\'t exist'),
    'content_release_not_preview': _('This is not a preview release'),
    'content_release_not_stage': _('This is not a stage release'),
    'content_release_not_live': _('This is not a live release'),
    'content_release_stage_alreay_exists': _('Stage Content Release alredy exists'),
    'content_release_already_stage': _('Content Release alredy staged'),
    'content_release_already_live': _('Content Release alredy live'),
    'no_content_release_stage': _('No Stage Content Release'),
}


class PublisherAPI:
    """ PublisherAPI """

    def __init__(self, api_type='django'):
        if api_type not in API_TYPES:
            raise ValueError(ERROR_STATUS_CODE['wrong_api_type'])
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

    def add_content_release(self, site_code, title, version, parameters=None,
                            based_on_release_uuid=None, use_current_live_as_base_release=False):
        """ add_content_release """
        try:
            content_release = ContentRelease.objects.get(
                site_code=site_code,
                title=title,
                version=version,
            )
            self.update_content_release_parameters(site_code, content_release.uuid, parameters)
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
                use_current_live_as_base_release=use_current_live_as_base_release,
            )
            content_release.save()
            self.update_content_release_parameters(site_code, content_release.uuid, parameters)
            return self.send_response('success', content_release)

    def update_content_release_parameters(self, site_code, release_uuid, parameters,
                                          clear_first=False):
        """ update_content_release_parameters """
        try:
            content_release = ContentRelease.objects.get(
                site_code=site_code,
                uuid=release_uuid,
            )

            if clear_first:
                ContentReleaseExtraParameter.objects.filter(
                    content_release=content_release).delete()

            if parameters:
                for key, value in parameters.items():
                    ContentReleaseExtraParameter.objects.update_or_create(
                        key=key,
                        content_release=content_release,
                        defaults={
                            'content': value,
                        }
                    )
            
            return self.send_response('success')

        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def get_extra_paramater(self, site_code, release_uuid, key):
        """ get_extra_paramater """
        try:
            extra_parameter = ContentReleaseExtraParameter.objects.get(
                content_release__site_code=site_code,
                content_release__uuid=release_uuid,
                key=key,
            )
            return self.send_response('success', extra_parameter.content)
        except ContentReleaseExtraParameter.DoesNotExist:
            return self.send_response('content_release_extra_parameter_does_not_exist')

    def get_extra_paramaters(self, site_code, release_uuid):
        """ get_extra_paramaters """
        extra_parameters = ContentReleaseExtraParameter.objects.filter(
            content_release__site_code=site_code,
            content_release__uuid=release_uuid,
        )
        return self.send_response('success', extra_parameters)

    def remove_content_release(self, site_code, release_uuid):
        """ remove_content_release """
        try:
            ContentRelease.objects.get(site_code=site_code, uuid=release_uuid).delete()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def update_content_release(self, site_code, release_uuid, title=None, version=None,
                               parameters=None):
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
            self.update_content_release_parameters(site_code, release_uuid, parameters)
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def get_content_release_details(self, site_code, release_uuid, parameters=None):
        """ get_content_release_details """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            return self.send_response('success', content_release)
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def get_content_release_details_query_parameters(self, site_code, parameters):
        """ get_content_release_details_query_parameters """
        if not parameters:
            return self.send_response('parameters_missing')

        filters = []
        for key, value in parameters.items():
            filters.append(Q(key=key, content=value))

        extra_parameter = ContentReleaseExtraParameter.objects.filter(
            content_release__site_code=site_code,
        ).filter(reduce(lambda x, y: x | y, filters))

        if not extra_parameter.exists():
            return self.send_response('content_release_does_not_exist')

        list_by_releases = extra_parameter.values('content_release').annotate(cr_count=Count(
            'content_release'))

        if list_by_releases.filter(cr_count=len(parameters)).count() > 1:
            return self.send_response('content_release_more_than_one')

        content_release_id = list_by_releases.get(cr_count=len(parameters))['content_release']
        return self.send_response('success', ContentRelease.objects.get(
            site_code=site_code,
            id=content_release_id
        ))

    def get_stage_content_release(self, site_code, parameters=None):
        """ get_stage_content_release """
        try:
            stage_content_release = ContentRelease.objects.stage(site_code)
            return self.send_response('success', stage_content_release)
        except ContentRelease.DoesNotExist:
            return self.send_response('no_content_release_stage')

    def get_live_content_release(self, site_code, parameters=None):
        """ get_live_content_release """
        try:
            live_content_release = ContentRelease.objects.live(site_code)
            return self.send_response('success', live_content_release)
        except ContentRelease.DoesNotExist:
            return self.send_response('no_content_release_live')

    def set_stage_content_release(self, site_code, release_uuid):
        """ set_stage_content_release """
        content_release = None
        stage_content_release = None
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

        try:
            stage_content_release = ContentRelease.objects.get(
                site_code=site_code,
                uuid=release_uuid,
                status=1,
                is_stage=True,
            )
            return self.send_response('content_release_stage_alreay_exists')
        except ContentRelease.DoesNotExist:
            pass

        try:
            if content_release == ContentRelease.objects.live(site_code):
                return self.send_response('content_release_already_live')
        except ContentRelease.DoesNotExist:
            pass

        if content_release == stage_content_release:
            return self.send_response('content_release_already_stage')

        if content_release.status == 0:
            # content_release.copy_document_stage_releases(site_code)
            content_release.copy_document_release_ref_from_baserelease()
            content_release.status = 1
            content_release.is_stage = True
            content_release.save()
            return self.send_response('success')
        else:
            return self.send_response('content_release_not_preview')

    def unset_stage_content_release(self, site_code, release_uuid):
        pass
        # """ set_stage_content_release """
        # try:
        #     content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
        #     if content_release.status == 0 and content_release.is_stage:
        #         content_release.copy_document_stage_releases(site_code)
        #         content_release.status = 1
        #         content_release.save()
        #         return self.send_response('success')
        #     else:
        #         return self.send_response('content_release_not_preview')
        # except ContentRelease.DoesNotExist:
        #     return self.send_response('content_release_does_not_exist')

    def set_live_content_release(self, site_code, release_uuid):
        """ set_live_content_release """
        content_release = None
        live_content_release = None
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

        try:
            live_content_release = ContentRelease.objects.get(
                site_code=site_code,
                status=2,
                is_live=True,
            )
        except ContentRelease.DoesNotExist:
            pass

        if content_release == live_content_release:
            return self.send_response('content_release_already_live')

        if content_release.status == 1 and content_release.is_stage:
            content_release.status = 2
            content_release.publish_datetime = timezone.now()
            content_release.is_stage = False
            content_release.is_live = True
            content_release.save()
            if live_content_release:
                live_content_release.status = 3
                live_content_release.is_live = False
                live_content_release.save()
            return self.send_response('success')
        else:
            return self.send_response('content_release_not_stage')

    # def freeze_content_release(self, site_code, release_uuid, publish_datetime):
    #     """ freeze_content_release """
    #     try:
    #         if publish_datetime < timezone.now():
    #             return self.send_response('publishdatetime_in_past')
    #         content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
    #         content_release.status = 1
    #         content_release.publish_datetime = publish_datetime
    #         content_release.save()
    #         return self.send_response('success')
    #     except ContentRelease.DoesNotExist:
    #         return self.send_response('content_release_does_not_exist')
    #     except TypeError:
    #         return self.send_response('not_datetime')

    # def unfreeze_content_release(self, site_code, release_uuid):
    #     """ unfreeze_content_release """
    #     try:
    #         content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
    #         if ContentRelease.objects.is_published(release_uuid):
    #             return self.send_response('content_release_publish')
    #         content_release.status = 0
    #         content_release.save()
    #         return self.send_response('success')
    #     except ContentRelease.DoesNotExist:
    #         return self.send_response('content_release_does_not_exist')

    # def archive_content_release(self, site_code, release_uuid):
    #     """ archive_content_release """
    #     try:
    #         content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
    #         if not ContentRelease.objects.is_published(release_uuid):
    #             return self.send_response('content_release_not_publish')
    #         content_release.status = 2
    #         content_release.save()
    #         return self.send_response('success')
    #     except ContentRelease.DoesNotExist:
    #         return self.send_response('content_release_does_not_exist')

    # def unarchive_content_release(self, site_code, release_uuid):
    #     """ unarchive_content_release """
    #     try:
    #         content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
    #         if not ContentRelease.objects.is_published(release_uuid):
    #             return self.send_response('content_release_not_publish')
    #         content_release.status = 1
    #         content_release.save()
    #         return self.send_response('success')
    #     except ContentRelease.DoesNotExist:
    #         return self.send_response('content_release_does_not_exist')

    def list_content_releases(self, site_code, status=None, after=None):
        """ list_content_releases """
        content_releases = ContentRelease.objects.filter(site_code=site_code)
        if status:
            content_releases = content_releases.filter(status=status)
        if after:
            content_releases = content_releases.filter(publish_datetime__gte=after)
        return self.send_response('success', content_releases)

    def get_document_from_content_release(self, site_code, release_uuid, document_key,
                                          content_type='content'):
        """get_document_from_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            release_document = ReleaseDocument.objects.get(
                document_key=document_key,
                content_type=content_type,
                content_releases=content_release.id,
            )
            return self.send_response('success', release_document)
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
        except ReleaseDocument.DoesNotExist:
            return self.send_response('release_document_does_not_exist')

    def get_document_extra_from_content_release(self, site_code, release_uuid, document_key,
                                                content_type='content'):
        """get_document_extra_from_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            release_document = ReleaseDocument.objects.get(
                document_key=document_key,
                content_type=content_type,
                content_releases=content_release.id,
            )
            extra_parameters = ReleaseDocumentExtraParameter.objects.filter(
                release_document=release_document,
            )
            return self.send_response('success', extra_parameters)
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
        except ReleaseDocument.DoesNotExist:
            return self.send_response('release_document_does_not_exist')

    def publish_document_to_content_release(self, site_code, release_uuid, document_json,
                                            document_key, content_type='content', parameters=None):
        """ publish_document_to_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            created = False
            try:
                release_document = None
                release_document = ReleaseDocument.objects.get(
                    document_key=document_key,
                    content_releases=content_release.id,
                    content_type=content_type,
                )
                release_document.document_json = document_json
                release_document.deleted = False
                release_document.save()

                # clear then store parameters
                ReleaseDocumentExtraParameter.objects.filter(
                    release_document=release_document).delete()
            except ReleaseDocument.DoesNotExist:
                release_document = ReleaseDocument(
                    document_key=document_key,
                    content_type=content_type,
                    document_json=document_json,
                )
                release_document.save()
                content_release.release_documents.add(release_document)
                content_release.save()
                created = True

            # store parameters
            if parameters:
                for key, value in parameters.items():
                    extra_parameter = ReleaseDocumentExtraParameter(
                        key=key,
                        content=value,
                        release_document=release_document,
                    )
                    extra_parameter.save()

            return self.send_response('success', {'created': created})
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def unpublish_document_from_content_release(self, site_code, release_uuid, document_key,
                                                content_type='content'):
        """ unpublish_document_from_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            release_document = ReleaseDocument.objects.get(
                document_key=document_key,
                content_type=content_type,
                content_releases__id=content_release.id,
            )
            release_document.delete()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
        except ReleaseDocument.DoesNotExist:
            return self.send_response('release_document_does_not_exist')

    def delete_document_from_content_release(self, site_code, release_uuid, document_key,
                                             content_type='content'):
        """ delete_document_from_content_release """
        try:
            content_release = ContentRelease.objects.get(site_code=site_code, uuid=release_uuid)
            release_document, created = ReleaseDocument.objects.update_or_create(
                document_key=document_key,
                content_type=content_type,
                content_releases__id=content_release.id,
                defaults={
                    'document_json': None,
                    'deleted': True,
                }
            )
            if created:
                content_release.release_documents.add(release_document)
                content_release.save()
            return self.send_response('success')
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')

    def compare_content_releases(self, site_code, my_release_uuid, compare_to_release_uuid):
        """ compare_content_releases """
        try:
            comparison = []

            # get my_content_release documents
            my_content_release = ContentRelease.objects.get(
                site_code=site_code, uuid=my_release_uuid)
            releases = [my_content_release]
            if my_content_release.use_current_live_as_base_release:
                releases.append(ContentRelease.objects.live(my_content_release.site_code))
            elif my_content_release.base_release:
                releases.append(my_content_release.base_release)
            my_release_documents = ReleaseDocument.objects.filter(
                content_releases__in=releases,
            ).annotate(
                key_content=Concat(
                    'document_key', V('__'), 'content_type'),
            ).values_list('key_content', flat=True)

            # get compare_to_content_release documents
            compare_to_content_release = ContentRelease.objects.get(
                site_code=site_code, uuid=compare_to_release_uuid)
            releases = [compare_to_content_release]
            if compare_to_content_release.use_current_live_as_base_release:
                releases.append(ContentRelease.objects.live(my_content_release.site_code))
            elif compare_to_content_release.base_release:
                releases.append(compare_to_content_release.base_release)
            compare_to_release_documents = ReleaseDocument.objects.filter(
                content_releases__in=releases,
            ).annotate(
                key_content=Concat(
                    'document_key', V('__'), 'content_type'),
            ).values_list('key_content', flat=True)

            # get added document
            added_release_document = ReleaseDocument.objects.annotate(
                key_content=Concat(
                    'document_key', V('__'), 'content_type'),
                diff=V('Added', output_field=CharField()),
            ).exclude(
                key_content__in=compare_to_release_documents,
            ).filter(
                key_content__in=my_release_documents,
            ).values(
                'document_key', 'content_type', 'diff'
            ).distinct()

            # get removed document
            removed_release_document = ReleaseDocument.objects.annotate(
                key_content=Concat(
                    'document_key', V('__'), 'content_type'),
                diff=V('Removed', output_field=CharField()),
            ).filter(
                key_content__in=compare_to_release_documents,
            ).exclude(
                key_content__in=my_release_documents,
            ).values(
                'document_key', 'content_type', 'diff'
            ).distinct()

            # get changed document
            changed_release_document = ReleaseDocument.objects.annotate(
                key_content=Concat(
                    'document_key', V('__'), 'content_type'),
                diff=Case(
                    When(deleted=True, then=V('Removed')),
                    default=V('Changed'),
                    output_field=CharField(),
                ),
            ).filter(
                key_content__in=set(compare_to_release_documents) & set(my_release_documents),
            ).values(
                'key_content', 'document_key', 'content_type', 'diff', 'deleted'
            ).annotate(
                count_key_content=Count('key_content'),
            ).filter(
                Q(count_key_content__gt=1) | Q(deleted=True)
            ).values(
                'document_key', 'content_type', 'diff',
            ).distinct()

            # get extra
            release_documents = list(added_release_document) + \
                                list(removed_release_document) + \
                                list(changed_release_document)

            for release_document in release_documents:
                if release_document['diff'] in ['Added', 'Removed']:
                    extra_parameters = ReleaseDocumentExtraParameter.objects.filter(
                        release_document__document_key=release_document['document_key'],
                        release_document__content_type=release_document['content_type'],
                        release_document__content_releases=my_content_release.id \
                            if release_document['diff'] == 'Added' else \
                                compare_to_content_release.id,
                    ).values(
                        'key', 'content'
                    )

                    if extra_parameters.exists():
                        release_document.update({
                            'parameters': {p['key']:p['content'] for p in extra_parameters}
                        })

                if release_document['diff'] == 'Changed':
                    new_extra_parameters = ReleaseDocumentExtraParameter.objects.filter(
                        release_document__document_key=release_document['document_key'],
                        release_document__content_type=release_document['content_type'],
                        release_document__content_releases=my_content_release.id
                    ).values(
                        'key', 'content'
                    )
                    old_extra_parameters = ReleaseDocumentExtraParameter.objects.filter(
                        release_document__document_key=release_document['document_key'],
                        release_document__content_type=release_document['content_type'],
                        release_document__content_releases=compare_to_content_release.id
                    ).values(
                        'key', 'content'
                    )

                    if new_extra_parameters.exists() or old_extra_parameters.exists():
                        release_document.update({
                            'parameters': {
                                'release_from': {
                                    p['key']:p['content'] for p in new_extra_parameters
                                },
                                'release_compare_to': {
                                    p['key']:p['content'] for p in old_extra_parameters
                                },
                            }
                        })

            # sort comparison dict
            comparison = sorted(release_documents, key=itemgetter(
                'diff', 'content_type', 'document_key'))
            return self.send_response('success', comparison)
        except ContentRelease.DoesNotExist:
            return self.send_response('content_release_does_not_exist')
