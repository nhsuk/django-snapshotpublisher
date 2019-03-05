import json
import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase

from djangosnapshotpublisher.models import ContentRelease
from djangosnapshotpublisher.publisher_api import PublisherAPI


class ContentReleaseTestCase(TestCase):

    def setUp(self):
        pass

    def test_version(self):
        """wrong version format"""
        content_release = ContentRelease(
            version='0.1sdf.1',
            title='test1',
            site_code='site1',
        )
        try:
            content_release.save()
            self.fail('Validation Error should be raised')
        except ValidationError as e:
            self.assertEquals('version_wrong_format', e.code)

        """0.0.0 version"""
        content_release = ContentRelease(
            version='0.0.0',
            title='test1',
            site_code='site1',
        )
        try:
            content_release.save()
            self.fail('Validation Error should be raised')
        except ValidationError as e:
            self.assertEquals('version_none', e.code)

        """version > one or more frozen or archived release"""
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
        except ValidationError as e:
            self.assertEquals('version_conflict_live_releases', e.code)


class PublisherAPITestCase(TestCase):

    def setUp(self):
        self.publisher_api = PublisherAPI(api_type='django')

    def test_add_content_release(self):
        """ Create a ContentRelease """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = ContentRelease.objects.get(site_code='site1', title='title1', version='0.0.1')
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'], content_release)

        """ Try to create a ContentRelease that alredy exist """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_already_exists')
   
    def test_remove_content_release(self):
        """ Try to remove a ContentRelease that doesn't exist """
        response = self.publisher_api.remove_content_release('site1', uuid.uuid4())
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_does_not_exist')

        """ Create a ContentRelease """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = ContentRelease.objects.get(site_code='site1', title='title1', version='0.0.1')
        self.assertEquals(response['status'], 'success')

        """ Remove a ContentRelease """
        response = self.publisher_api.remove_content_release('site1', content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertFalse(ContentRelease.objects.filter(site_code='site1', uuid=content_release.uuid).exists())

    def test_update_content_release(self):
        """ Try to update a ContentRelease that doesn't exist """
        response = self.publisher_api.update_content_release('site1', uuid.uuid4(), **{'title': 'title1'})
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_does_not_exist')

        """ Update title and version for a ContentRelease """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        self.assertEquals(response['status'], 'success')
        response = self.publisher_api.update_content_release('site1', content_release.uuid, **{
            'title': 'title2',
            'version': '0.0.2',
        })
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(content_release.title, 'title2')
        self.assertEquals(content_release.version, '0.0.2')

        """ Update without title and version """
        response = self.publisher_api.update_content_release('site1', uuid.uuid4())
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_title_version_not_defined')

    def test_get_content_release_details(self):
        """ Try to get a ContentRelease that doesn't exist """
        response = self.publisher_api.get_content_release_details('site1', uuid.uuid4())
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_does_not_exist')

        """ get ContentRelease """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        self.assertEquals(response['status'], 'success')
        response = self.publisher_api.get_content_release_details('site1', content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'], content_release)


class PublisherAPIJsonTestCase(TestCase):

    def setUp(self):
        self.publisher_api = PublisherAPI(api_type='json')

    def test_add_content_release(self):
        """ Create a ContentRelease """
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = ContentRelease.objects.get(site_code='site1', title='title1', version='0.0.1')
        response = json.loads(response_json)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'], {
            'id': response['content']['id'],
            'uuid': response['content']['uuid'],
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PENDING',
            'publish_datetime': None,
            'base_release': None,
        })

        """ Try to create a ContentRelease that alredy exist """
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_already_exists')
   
    def test_remove_content_release(self):
        """ Create a ContentRelease """
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release_uuid = response['content']['uuid']
        """ Remove a ContentRelease """
        response_json = self.publisher_api.remove_content_release('site1', content_release_uuid)
        response = json.loads(response_json)
        self.assertEquals(response['status'], 'success')
        self.assertFalse(ContentRelease.objects.filter(site_code='site1', uuid=content_release_uuid).exists())

    def test_update_content_release(self):
        """ Update title and version for a ContentRelease """
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release_uuid = response['content']['uuid']
        response = self.publisher_api.update_content_release('site1', content_release_uuid, **{
            'title': 'title2',
            'version': '0.0.2',
        })
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=content_release_uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(content_release.title, 'title2')
        self.assertEquals(content_release.version, '0.0.2')
    
    def test_get_content_release_details(self):
        """ get ContentRelease """
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        self.assertEquals(response['status'], 'success')
        response_json = self.publisher_api.get_content_release_details('site1', content_release.uuid)
        response = json.loads(response_json)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'], {
            'id': content_release.id,
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PENDING',
            'publish_datetime': None,
            'base_release': None,
        })