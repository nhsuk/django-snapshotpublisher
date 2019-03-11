"""
.. module:: djangosnapshotpublisher.tests
   :synopsis: djangosnapshotpublisher unittest
"""

import json
import uuid

from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from djangosnapshotpublisher.models import ContentRelease, ReleaseDocument, ContentReleaseExtraParameter
from djangosnapshotpublisher.publisher_api import PublisherAPI, DATETIME_FORMAT


class ContentReleaseTestCase(TestCase):
    """ unittest for ReleaseDocument model """

    def setUp(self):
        """ setUp """
        pass

    def test_version(self):
        """ unittest for version attribute validation """

        # wrong version format
        content_release = ContentRelease(
            version='0.1sdf.1',
            title='test1',
            site_code='site1',
        )
        try:
            content_release.save()
            self.fail('Validation Error should be raised')
        except ValidationError as v_e:
            self.assertEqual('version_wrong_format', v_e.code)

        # 0.0.0 version
        content_release = ContentRelease(
            version='0.0.0',
            title='test1',
            site_code='site1',
        )
        try:
            content_release.save()
            self.fail('Validation Error should be raised')
        except ValidationError as v_e:
            self.assertEqual('version_none', v_e.code)

        # version > one or more frozen or archived release
        content_release1 = ContentRelease(
            version='1.2.1',
            title='test1',
            site_code='site1',
            status=1,
        )
        content_release1.save()

        content_release2 = ContentRelease(
            version='1.2.0',
            title='test2',
            site_code='site1',
        )

        try:
            content_release2.save()
            self.fail('Validation Error should be raised')
        except ValidationError as v_e:
            self.assertEqual('version_conflict_live_releases', v_e.code)

    def test_base_release(self):
        """ unittest for base_release attribute validation """
        # use_current_live_as_base_release True
        content_release1 = ContentRelease(
            version='0.1',
            title='test1',
            site_code='site1',
            status=0,
            use_current_live_as_base_release=True,
        )
        content_release1.save()

        # use_current_live_as_base_release False and base_release not None
        content_release2 = ContentRelease(
            version='0.2',
            title='test2',
            site_code='site1',
            status=0,
            use_current_live_as_base_release=False,
            base_release=content_release1,
        )
        content_release2.save()

        # use_current_live_as_base_release True and base_release not None
        try:
            content_release2.use_current_live_as_base_release = True
            content_release2.save()
        except ValidationError as v_e:
            self.assertEqual('base_release_should_be_none', v_e.code)

    def test_set_live(self):
        """ unittest when content release go live """
        self.publisher_api = PublisherAPI(api_type='django')
        response = self.publisher_api.add_content_release('site1', 'title1', '0.1')
        content_release = response['content']
        document_json = json.dumps({'page_title': 'Test'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            'key1',
        )
        self.publisher_api.set_live_content_release('site1', content_release.uuid)
        self.publisher_api.get_live_content_release('site1')

        # set live, not base release
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.2')
        content_release2 = response['content']
        document_json2 = json.dumps({'page_title': 'Test2'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json2,
            'key1',
        )
        document_json3 = json.dumps({'page_title': 'Test3'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json3,
            'key2',
        )
        self.publisher_api.set_live_content_release('site1', content_release2.uuid)
        self.publisher_api.get_live_content_release('site1')
        content_release2 = ContentRelease.objects.get(uuid=content_release2.uuid)
        self.assertEqual(content_release2.release_documents.count(), 2)
        release_document1 = content_release2.release_documents.get(
            document_key='key1',
        )
        release_document2 = content_release2.release_documents.get(
            document_key='key2',
        )
        self.assertEqual(json.loads(release_document1.document_json), {'page_title': 'Test2'})
        self.assertEqual(json.loads(release_document2.document_json), {'page_title': 'Test3'})

        # copy base release documents
        response = self.publisher_api.add_content_release(
            'site1', 'title3', '0.3', None, content_release2.uuid)
        content_release3 = response['content']
        document_json4 = json.dumps({'page_title': 'Test4'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release3.uuid,
            document_json4,
            'key2',
        )
        self.publisher_api.set_live_content_release('site1', content_release3.uuid)

        # publish to content release and get the last one and check in the copy works
        response = self.publisher_api.add_content_release(
            'site1', 'title4', '0.4', None, None, True)
        content_release4 = response['content']
        document_json5 = json.dumps({'page_title': 'Test5'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release4.uuid,
            document_json5,
            'key1',
        )
        self.publisher_api.set_live_content_release('site1', content_release4.uuid)

        self.publisher_api.get_live_content_release('site1')
        content_release3 = ContentRelease.objects.get(uuid=content_release3.uuid)
        self.assertEqual(content_release3.release_documents.count(), 2)
        release_document1 = content_release3.release_documents.get(
            document_key='key1',
        )
        release_document2 = content_release3.release_documents.get(
            document_key='key2',
        )
        self.assertEqual(json.loads(release_document1.document_json), {'page_title': 'Test2'})
        self.assertEqual(json.loads(release_document2.document_json), {'page_title': 'Test4'})

        content_release4 = ContentRelease.objects.get(uuid=content_release4.uuid)
        self.assertEqual(content_release4.release_documents.count(), 2)
        release_document1 = content_release4.release_documents.get(
            document_key='key1',
        )
        release_document2 = content_release4.release_documents.get(
            document_key='key2',
        )
        self.assertEqual(json.loads(release_document1.document_json), {'page_title': 'Test5'})
        self.assertEqual(json.loads(release_document2.document_json), {'page_title': 'Test4'})


class PublisherAPITestCase(TestCase):
    """ unittest for ublisherAPITest with api_type=django """

    def setUp(self):
        """ setUp """
        self.publisher_api = PublisherAPI(api_type='django')
        self.datetime_past = timezone.now() - timezone.timedelta(minutes=10)
        self.datetime_future = timezone.now() + timezone.timedelta(minutes=10)

    def test_add_content_release(self):
        """ unittest for add_content_release """

        #  Create a ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = ContentRelease.objects.get(
            site_code='site1', title='title1', version='0.0.1')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

        #  Try to create a ContentRelease that alredy exist
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_already_exists')

        #  Try to create a Base ContentRelease that alredy exist
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', None, uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'base_content_release_does_not_exist')

        #  Create a ContentRelease with Base ContentRelease
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', None, content_release.uuid)
        content_release = ContentRelease.objects.get(
            site_code='site1', title='title2', version='0.0.2')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

        #  Create a ContentRelease with extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.3', parameters, None, False)
        content_release = ContentRelease.objects.get(
            site_code='site1', title='title2', version='0.0.3')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)
        extra_parameters = ContentReleaseExtraParameter.objects.filter(
            content_release=content_release,
        )
        self.assertEqual(extra_parameters.count(), 2)
        for extra_parameter in extra_parameters:
            self.assertEqual(extra_parameter.content, parameters[extra_parameter.key])

    def test_remove_content_release(self):
        """ unittest for remove_content_release """

        #  Try to remove a ContentRelease that doesn't exist
        response = self.publisher_api.remove_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Create a ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = ContentRelease.objects.get(
            site_code='site1', title='title1', version='0.0.1')
        self.assertEqual(response['status'], 'success')

        #  Remove a ContentRelease
        response = self.publisher_api.remove_content_release('site1', content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertFalse(ContentRelease.objects.filter(
            site_code='site1', uuid=content_release.uuid).exists())
        
        #  Remove a ContentRelease with extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', parameters, None, False)
        self.assertEqual(response['status'], 'success')
        response = self.publisher_api.remove_content_release('site1', content_release.uuid)
        self.assertFalse(ContentRelease.objects.filter(
            site_code='site1', uuid=content_release.uuid).exists())
        self.assertFalse(ContentReleaseExtraParameter.objects.filter(
            content_release=content_release).exists())

    def test_update_content_release(self):
        """ unittest for update_content_release """

        #  Try to update a ContentRelease that doesn't exist
        response = self.publisher_api.update_content_release(
            'site1', uuid.uuid4(), **{'title': 'title1'})
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Update title and version for a ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        self.assertEqual(response['status'], 'success')
        response = self.publisher_api.update_content_release('site1', content_release.uuid, **{
            'title': 'title2',
            'version': '0.0.2',
        })
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.title, 'title2')
        self.assertEqual(content_release.version, '0.0.2')

        #  Update without title and version
        response = self.publisher_api.update_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_title_version_not_defined')

        #  Update without extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.update_content_release('site1', content_release.uuid, **{
            'title': 'title3',
            'version': '0.0.2',
            'parameters': parameters,
        })
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.title, 'title3')
        self.assertEqual(content_release.version, '0.0.2')
        extra_parameters = ContentReleaseExtraParameter.objects.filter(
            content_release=content_release,
        )
        self.assertEqual(extra_parameters.count(), 2)
        for extra_parameter in extra_parameters:
            self.assertEqual(extra_parameter.content, parameters[extra_parameter.key])

    def test_get_content_release_details(self):
        """ unittest for get_content_release_details """

        #  Try to get a ContentRelease that doesn't exist
        response = self.publisher_api.get_content_release_details('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  get ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        self.assertEqual(response['status'], 'success')
        response = self.publisher_api.get_content_release_details('site1', content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

    def test_get_content_release_details_query_parameters(self):
        """ unittest for get_content_release_details_query_parameters """

        #  missing parameters
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', None)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'parameters_missing')

        #  Try to get a ContentRelease that doesn't exist
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', {'frontend_id': 'v0.1', 'domain': 'test.co.uk'})
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        # Get content release
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title1', '0.0.1', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', {'frontend_id': 'v0.1', 'domain': 'test.co.uk'})
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

        # Get content release more than one same domain but different frontend
        parameters = {'frontend_id': 'v0.2', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', {'frontend_id': 'v0.2', 'domain': 'test.co.uk'})
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

        # Get content release more than one
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title3', '0.0.3', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', {'frontend_id': 'v0.1', 'domain': 'test.co.uk'})
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_more_than_one')
    
    def test_get_extra_paramater(self):
        """ unittest for test_get_extra_paramater """

        #  ContentReleaseExtraParameter doesn't exist
        response = self.publisher_api.get_extra_paramater('site1', uuid.uuid4(), 'frontend_id')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_extra_parameter_does_not_exist')

        # get extra parameter
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title1', '0.0.1', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_extra_paramater('site1', content_release.uuid, 'frontend_id')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], parameters['frontend_id'])
    
    def test_get_extra_paramaters(self):
        """ unittest for test_get_extra_paramater """

        #  No ContentReleaseExtraParameter
        response = self.publisher_api.get_extra_paramaters('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'success')
        self.assertEqual(type(response['content']), QuerySet)
        self.assertEqual(response['content'].count(), 0)

        # get extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title1', '0.0.1', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_extra_paramaters('site1', content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'].count(), 2)
        self.assertEqual(response['content'].get(key='frontend_id').content, parameters['frontend_id'])
        self.assertEqual(response['content'].get(key='domain').content, parameters['domain'])

    def test_get_live_content_release(self):
        """ unittest for get_live_content_release """

        #  No ContentRelease
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')

        #  No ContentRelease in the past or null
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')
        content_release.publish_datetime = timezone.now() + timezone.timedelta(days=1)
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')

        #  ContentRelease in the past archived or pending
        content_release.publish_datetime = timezone.now() - timezone.timedelta(days=1)
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')
        content_release.status = 2
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')

        #  Get live ContentRelease
        content_release.status = 1
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

        #  Get latest live release
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
        content_release2 = response['content']
        content_release2.status = 1
        content_release2.publish_datetime = timezone.now() - timezone.timedelta(hours=1)
        content_release2.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release2)

    def test_set_live_content_release(self):
        """ unittest for set_live_content_release """

        #  No ContentRelease
        response = self.publisher_api.set_live_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Set the ContentRelease live
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.set_live_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.status, 1)
        self.assertGreater(timezone.now(), content_release.publish_datetime)
        self.assertGreater(
            content_release.publish_datetime, timezone.now() - timezone.timedelta(minutes=5))

    def test_freeze_content_release(self):
        """ unittest for freeze_content_release """

        #  No ContentRelease
        response = self.publisher_api.freeze_content_release(
            'site1',
            uuid.uuid4(),
            self.datetime_future.strftime(DATETIME_FORMAT),
        )
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Wrong datetime format
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.freeze_content_release(
            'site1',
            content_release.uuid,
            self.datetime_future.strftime('%H:%M:%S %d-%m-%Y'),
        )
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'wrong_datetime_format')

        #  Publishdatetime in the past
        response = self.publisher_api.freeze_content_release(
            'site1',
            content_release.uuid,
            self.datetime_past.strftime(DATETIME_FORMAT),
        )
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'publishdatetime_in_past')

        #  Freeze the ContentRelease
        response = self.publisher_api.freeze_content_release(
            'site1',
            content_release.uuid,
            self.datetime_future.strftime(DATETIME_FORMAT),
        )
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.status, 1)
        self.assertEqual(
            content_release.publish_datetime.strftime(DATETIME_FORMAT),
            self.datetime_future.strftime(DATETIME_FORMAT)
        )

    def test_unfreeze_content_release(self):
        """ unittest for unfreeze_content_release """

        #  No ContentRelease
        response = self.publisher_api.unfreeze_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Unfreeze the ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.unfreeze_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.status, 0)
        content_release.publish_datetime = self.datetime_future
        content_release.save()
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.status, 0)

        #  ContentRelease is published
        content_release.publish_datetime = self.datetime_past
        content_release.save()
        response = self.publisher_api.unfreeze_content_release('site1', content_release.uuid)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_publish')

    def test_archive_content_release(self):
        """ unittest for archive_content_release """

        #  No ContentRelease
        response = self.publisher_api.archive_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  ContentRelease is not published
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.archive_content_release('site1', content_release.uuid)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_not_publish')
        content_release.publish_datetime = self.datetime_future
        content_release.save()
        response = self.publisher_api.archive_content_release('site1', content_release.uuid)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_not_publish')

        #  Archive the ContentRelease
        content_release.publish_datetime = self.datetime_past
        content_release.save()
        response = self.publisher_api.archive_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.status, 2)

    def test_unarchive_content_release(self):
        """ unittest for unarchive_content_release """

        #  No ContentRelease
        response = self.publisher_api.unarchive_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  ContentRelease is not published
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_not_publish')
        content_release.publish_datetime = self.datetime_future
        content_release.save()
        response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_not_publish')

        #  Unarchive the ContentRelease
        content_release.publish_datetime = self.datetime_past
        content_release.save()
        response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.status, 1)

    def test_list_content_releases(self):
        """ unittest for list_content_releases """

        #  No ContentRelease
        response = self.publisher_api.list_content_releases('site1')
        self.assertEqual(response['status'], 'success')
        self.assertFalse(response['content'].exists())

        #  List ContentReleases without defining status
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release1 = response['content']
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
        response = self.publisher_api.list_content_releases('site1')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'].count(), 2)

        #  List ContentReleases with status
        content_release1.status = 1
        content_release1.save()
        response = self.publisher_api.list_content_releases('site1', 1)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'].count(), 1)

    def test_get_document_from_content_release(self):
        """ unittest for get_document_from_content_release """

        document_key = 'key1'

        #  No ContentRelease
        response = self.publisher_api.get_document_from_content_release(
            'site1', uuid.uuid4(), document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  No ReleaseDocument
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')

        #  Get ReleaseDocument
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        release_document = ReleaseDocument.objects.get(
            document_key=document_key,
            content_releases__id=content_release.id)
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], release_document)

        #  Get ReleaseDocument with content_type
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key, 'page')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')
        release_document.content_type = 'page'
        release_document.save()
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key, 'page')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], release_document)

    def test_publish_document_to_content_release(self):
        """ unittest for publish_document_to_content_release """

        document_key = 'key1'

        #  No ContentRelease
        response = self.publisher_api.publish_document_to_content_release(
            'site1', uuid.uuid4(), '{}', document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Store ReleaseDocument
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        document_json = json.dumps({'page_title': 'Test page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content']['created'], True)
        release_document = ReleaseDocument.objects.get(
            document_key=document_key, content_releases__id=content_release.id)
        self.assertEqual(release_document.document_json, document_json)

        #  Try to store a new ReleaseDocument with same  key and content_release
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content']['created'], False)
        release_document = ReleaseDocument.objects.get(
            document_key=document_key, content_releases__id=content_release.id)
        self.assertEqual(release_document.document_json, document_json)

        #  Store ReleaseDocument with content_type
        document_json = json.dumps({'page_title': 'Test3 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
            'page',
        )
        self.publisher_api.get_live_content_release('site1')
        release_document = ReleaseDocument.objects.get(
            document_key=document_key,
            content_releases__id=content_release.id,
            content_type='page')
        self.assertEqual(response['status'], 'success')
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key, 'page')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], release_document)

    def test_unpublish_document_from_content_release(self):
        """ unittest for unpublish_document_to_content_release """

        #  No ContentRelease
        document_key = 'key1'
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', uuid.uuid4(), document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  No ReleaseDocument
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', content_release.uuid, document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')

        #  Unpublish ReleaseDocument
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', content_release.uuid, document_key)
        release_document = ReleaseDocument.objects.filter(
            document_key=document_key, content_releases__id=content_release.id)
        self.assertEqual(response['status'], 'success')
        self.assertFalse(release_document.exists())

        #  Unpublish ReleaseDocument content_type
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
            'page',
        )
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', content_release.uuid, document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', content_release.uuid, document_key, 'page')
        release_document = ReleaseDocument.objects.filter(
            document_key=document_key, content_releases__id=content_release.id, content_type='page')
        self.assertEqual(response['status'], 'success')
        self.assertFalse(release_document.exists())


class PublisherAPIJsonTestCase(TestCase):
    """ unittest for ublisherAPITest with api_type=json """

    def setUp(self):
        """ setUp """
        self.publisher_api = PublisherAPI(api_type='json')

    def test_add_content_release(self):
        """ unittest for add_content_release """

        #  Create a ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], {
            'uuid': response['content']['uuid'],
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PENDING',
            'publish_datetime': None,
            'use_current_live_as_base_release': False,
            'base_release': None,
        })

        #  Try to create a ContentRelease that alredy exist
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_already_exists')

    def test_remove_content_release(self):
        """ unittest for remove_content_release """

        #  Create a ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release_uuid = response['content']['uuid']
        #  Remove a ContentRelease
        response_json = self.publisher_api.remove_content_release('site1', content_release_uuid)
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertFalse(ContentRelease.objects.filter(
            site_code='site1', uuid=content_release_uuid).exists())

    def test_update_content_release(self):
        """ unittest for update_content_release """

        #  Update title and version for a ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release_uuid = response['content']['uuid']
        response = self.publisher_api.update_content_release('site1', content_release_uuid, **{
            'title': 'title2',
            'version': '0.0.2',
        })
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=content_release_uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.title, 'title2')
        self.assertEqual(content_release.version, '0.0.2')

    def test_get_content_release_details(self):
        """ unittest for get_content_release_details """

        #  get ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        self.assertEqual(response['status'], 'success')
        response_json = self.publisher_api.get_content_release_details(
            'site1', content_release.uuid)
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], {
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PENDING',
            'publish_datetime': None,
            'use_current_live_as_base_release': False,
            'base_release': None,
        })

    def test_get_live_content_release(self):
        """ unittest for get_live_content_release """

        #  Get live ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        content_release.status = 1
        content_release.publish_datetime = timezone.now() - timezone.timedelta(hours=1)
        content_release.save()
        response_json = self.publisher_api.get_live_content_release('site1')
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], {
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'FROZEN',
            'publish_datetime': response['content']['publish_datetime'],
            'use_current_live_as_base_release': False,
            'base_release': None,
        })

    def test_list_content_releases(self):
        """ unittest for list_content_releases """

        #  List Releases without defining status
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        response_json = self.publisher_api.list_content_releases('site1')
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(len(response['content']), 1)
        self.assertEqual(response['content'][0], {
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PENDING',
            'publish_datetime': response['content'][0]['publish_datetime'],
            'use_current_live_as_base_release': False,
            'base_release': None,
        })

    def test_get_document_from_content_release(self):
        """ unittest for get_document_from_content_release """

        document_key = 'key1'
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response_json = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        response_json = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key)
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], {
            'document_key': document_key,
            'document_json': document_json,
            'content_type': 'content',
        })
    
    def test_get_extra_paramaters(self):
        """ unittest for test_get_extra_paramater """

        # get extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response_json = self.publisher_api.add_content_release(
            'site1', 'title1', '0.0.1', parameters, None, False)
        response = json.loads(response_json)
        content_release = response['content']
        response_json = self.publisher_api.get_extra_paramaters('site1', content_release['uuid'])
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], [
            {
                'key': 'frontend_id',
                'content': 'v0.1',
                'content_release_uuid': content_release['uuid']
            },{
                'key': 'domain',
                'content': 'test.co.uk',
                'content_release_uuid': content_release['uuid']
            }
        ])
