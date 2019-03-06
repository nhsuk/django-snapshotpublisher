import json
import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from djangosnapshotpublisher.models import ContentRelease
from djangosnapshotpublisher.publisher_api import PublisherAPI, DATETIME_FORMAT


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
        self.datetime_past = timezone.now() - timezone.timedelta(minutes=10)
        self.datetime_future = timezone.now() + timezone.timedelta(minutes=10)

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

        """ Try to create a Base ContentRelease that alredy exist """
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2', uuid.uuid4())
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'base_content_release_does_not_exist')

        """ Create a ContentRelease with Base ContentRelease"""
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2', content_release.uuid)
        content_release = ContentRelease.objects.get(site_code='site1', title='title2', version='0.0.2')
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'], content_release)
   
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
    
    def test_get_live_content_release(self):
        """ No Release """
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'no_content_release_live')

        """ No release in the past or null"""
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'no_content_release_live')
        content_release.publish_datetime = timezone.now() + timezone.timedelta(days=1)
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'no_content_release_live')

        """ Release in the past archived or pending """
        content_release.publish_datetime = timezone.now() - timezone.timedelta(days=1)
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'no_content_release_live')
        content_release.status = 2
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'no_content_release_live')

        """ Get live release """
        content_release.status = 1
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'], content_release)

        """ Get latest live release"""
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
        content_release2 = response['content']
        content_release2.status = 1
        content_release2.publish_datetime = timezone.now() - timezone.timedelta(hours=1)
        content_release2.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'], content_release2)
    
    def test_set_live_content_release(self):
        """ No Release """
        response = self.publisher_api.set_live_content_release('site1', uuid.uuid4())
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_does_not_exist')

        """ Set the release live """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.set_live_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(content_release.status, 1)
        self.assertGreater(timezone.now(), content_release.publish_datetime)
        self.assertGreater(content_release.publish_datetime, timezone.now() - timezone.timedelta(minutes=5))

    def test_freeze_content_release(self):
        """ No Release """
        response = self.publisher_api.freeze_content_release(
            'site1',
            uuid.uuid4(),
            self.datetime_future.strftime(DATETIME_FORMAT),
        )
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_does_not_exist')

        """ Wrong datetime format """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.freeze_content_release(
            'site1',
            content_release.uuid,
            self.datetime_future.strftime('%H:%M:%S %d-%m-%Y'),
        )
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'wrong_datetime_format')

        """ Publishdatetime in the past """
        response = self.publisher_api.freeze_content_release(
            'site1',
            content_release.uuid,
            self.datetime_past.strftime(DATETIME_FORMAT),
        )
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'publishdatetime_in_past')

        """ Freeze the release """
        response = self.publisher_api.freeze_content_release(
            'site1',
            content_release.uuid,
            self.datetime_future.strftime(DATETIME_FORMAT),
        )
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(content_release.status, 1)
        self.assertEquals(
            content_release.publish_datetime.strftime(DATETIME_FORMAT),
            self.datetime_future.strftime(DATETIME_FORMAT)
        )

    def test_unfreeze_content_release(self):
        """ No Release """
        response = self.publisher_api.unfreeze_content_release('site1', uuid.uuid4())
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_does_not_exist')

        """ Unfreeze the release """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.unfreeze_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(content_release.status, 0)
        content_release.publish_datetime = self.datetime_future
        content_release.save()
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(content_release.status, 0)

        """ Release is published """
        content_release.publish_datetime = self.datetime_past
        content_release.save()
        response = self.publisher_api.unfreeze_content_release('site1', content_release.uuid)
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_publish')

    def test_archive_content_release(self):
        """ No Release """
        response = self.publisher_api.archive_content_release('site1', uuid.uuid4())
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_does_not_exist')

        """ Release is not published """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.archive_content_release('site1', content_release.uuid)
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_not_publish')
        content_release.publish_datetime = self.datetime_future
        content_release.save()
        response = self.publisher_api.archive_content_release('site1', content_release.uuid)
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_not_publish')

        """ Archive the release """
        content_release.publish_datetime = self.datetime_past
        content_release.save()
        response = self.publisher_api.archive_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(content_release.status, 2)
    
    def test_unarchive_content_release(self):
        """ No Release """
        response = self.publisher_api.unarchive_content_release('site1', uuid.uuid4())
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_does_not_exist')

        """ Release is not published """
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_not_publish')
        content_release.publish_datetime = self.datetime_future
        content_release.save()
        response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
        self.assertEquals(response['status'], 'error')
        self.assertEquals(response['error_code'], 'content_release_not_publish')

        """ Unarchive the release """
        content_release.publish_datetime = self.datetime_past
        content_release.save()
        response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(content_release.status, 1)
    
    def test_list_content_releases(self):
        """ No Release """
        response = self.publisher_api.list_content_releases('site1')
        self.assertEquals(response['status'], 'success')
        self.assertFalse(response['content'].exists())

        """ List Releases without defining status"""
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release1 = response['content']
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
        content_release2 = response['content']
        response = self.publisher_api.list_content_releases('site1')
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'].count(), 2)

        """ List Releases with status"""
        content_release1.status = 1
        content_release1.save()
        response = self.publisher_api.list_content_releases('site1', 1)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'].count(), 1)


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

    def test_get_live_content_release(self):
        """ Get live release """
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        content_release.status = 1
        content_release.publish_datetime = timezone.now() - timezone.timedelta(hours=1)
        content_release.save()
        response_json = self.publisher_api.get_live_content_release('site1')
        response = json.loads(response_json)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(response['content'], {
            'id': content_release.id,
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'FROZEN',
            'publish_datetime': response['content']['publish_datetime'],
            'base_release': None,
        })

    def test_list_content_releases(self):
        """ List Releases without defining status"""
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        response_json = self.publisher_api.list_content_releases('site1')
        response = json.loads(response_json)
        self.assertEquals(response['status'], 'success')
        self.assertEquals(len(response['content']), 1)
        self.assertEquals(response['content'][0], {
            'id': content_release.id,
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PENDING',
            'publish_datetime': response['content'][0]['publish_datetime'],
            'base_release': None,
        })