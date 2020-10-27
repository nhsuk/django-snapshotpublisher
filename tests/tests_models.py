"""
.. module:: djangosnapshotpublisher.tests
   :synopsis: djangosnapshotpublisher unittest
"""

import json
# import uuid

from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from djangosnapshotpublisher.admin import ContentReleaseAdmin
from djangosnapshotpublisher.models import ContentRelease, ContentReleaseExtraParameter
from djangosnapshotpublisher.publisher_api import PublisherAPI


class ContentReleaseTestCase(TestCase):
    """ unittest for ContentRelease model """

    def setUp(self):
        """ setUp """

    def test_admin(self):
        """ unittest for ContentReleaseAdmin """

        # check base_realse readonly when update ContentRelease
        site = AdminSite()
        content_release_admin = ContentReleaseAdmin(ContentRelease, site)

        content_release = ContentRelease(
            version='0.0.1',
            title='test1',
            site_code='site1',
            status=0,
        )
        content_release.save()

        self.assertEqual(content_release_admin.get_readonly_fields(None, None), [])
        self.assertEqual(
            content_release_admin.get_readonly_fields(None, content_release),
            ['base_release'],
        )

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
            base_release=None,
        )
        content_release2.save()

        # set base_release for a not live base_release
        try:
            content_release2.base_release = content_release1
            content_release2.save()
            self.fail('Validation Error should be raised')
        except ValidationError as v_e:
            self.assertEqual('base_release_should_be_none', v_e.code)

        # set base_release for a live base_release
        content_release1.status = 2
        content_release1.publish_datetime = timezone.now() - timezone.timedelta(minutes=10)
        content_release1.save()

        content_release2.base_release = content_release1
        content_release2.save()

        # use_current_live_as_base_release True and base_release not None - should receive validation error
        # only when release status is preview.
        try:
            content_release2.status = 0
            content_release2.use_current_live_as_base_release = True
            content_release2.save()
            self.fail('Validation Error should be raised')
        except ValidationError as v_e:
            self.assertEqual('base_release_should_be_none', v_e.code)

        content_release2.status = 1
        content_release2.use_current_live_as_base_release = True
        content_release2.save()


    def test_set_stage(self):
        """ unittest when content release go live """
        publisher_api = PublisherAPI(api_type='django')
        response = publisher_api.add_content_release('site1', 'title1', '0.1')
        content_release = response['content']
        document_json = json.dumps({'page_title': 'Test'})
        response = publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            'key1',
        )
        publisher_api.set_stage_content_release('site1', content_release.uuid)
        publisher_api.get_stage_content_release('site1')

    def test_set_live(self):
        """ unittest when content release go live """
        publisher_api = PublisherAPI(api_type='django')
        response = publisher_api.add_content_release('site1', 'title1', '0.1')
        content_release = response['content']
        document_json = json.dumps({'page_title': 'Test'})
        response = publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            'key1',
        )
        # set stage
        publisher_api.set_stage_content_release('site1', content_release.uuid)
        publisher_api.get_stage_content_release('site1')
        # set live
        publisher_api.set_live_content_release('site1', content_release.uuid)
        publisher_api.get_live_content_release('site1')

        # set live, not base release
        response = publisher_api.add_content_release(
            'site1', 'title2', '0.2')
        content_release2 = response['content']
        document_json2 = json.dumps({'page_title': 'Test2'})
        response = publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json2,
            'key1',
        )
        document_json3 = json.dumps({'page_title': 'Test3'})
        response = publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json3,
            'key2',
        )
        publisher_api.set_stage_content_release('site1', content_release2.uuid)
        publisher_api.get_stage_content_release('site1')
        publisher_api.set_live_content_release('site1', content_release2.uuid)
        publisher_api.get_live_content_release('site1')
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
        response = publisher_api.add_content_release(
            'site1', 'title3', '0.3', None, content_release2.uuid)
        content_release3 = response['content']
        document_json4 = json.dumps({'page_title': 'Test4'})
        response = publisher_api.publish_document_to_content_release(
            'site1',
            content_release3.uuid,
            document_json4,
            'key2',
        )
        publisher_api.set_stage_content_release('site1', content_release3.uuid)
        publisher_api.set_live_content_release('site1', content_release3.uuid)

        # publish to content release and get the last one and check in the copy works
        response = publisher_api.add_content_release(
            'site1', 'title4', '0.4', None, None, True)
        content_release4 = response['content']
        document_json5 = json.dumps({'page_title': 'Test5'})
        response = publisher_api.publish_document_to_content_release(
            'site1',
            content_release4.uuid,
            document_json5,
            'key1',
        )
        publisher_api.set_stage_content_release('site1', content_release4.uuid)
        publisher_api.get_stage_content_release('site1')
        publisher_api.set_live_content_release('site1', content_release4.uuid)
        publisher_api.get_live_content_release('site1')
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

        self.assertEqual(ContentRelease.objects.archived('site1').count(), 3)

    def test_copy_release(self):
        """ unittest copy ContentRelease """

        # create release
        publisher_api = PublisherAPI(api_type='django')
        response = publisher_api.add_content_release('site1', 'title1', '0.1', {
            'p1': 'test1',
            'p2': 'test2',
        })
        content_release = response['content']

        # add 2 documents to te release
        document_json = json.dumps({'page_title': 'Test1'})
        response = publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            'key1',
        )
        document_json = json.dumps({'page_title': 'Test2'})
        response = publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            'key2',
        )

        # copy release
        new_content_release = content_release.copy({'version': '0.2'})

        self.assertNotEqual(content_release.version, new_content_release.version)
        self.assertEqual(new_content_release.version, '0.2')
        content_release_values = ContentRelease.objects.values_list(
            'title',
            'site_code',
            'status',
            'publish_datetime',
            'use_current_live_as_base_release',
            'base_release',
            'is_live',
        )
        self.assertEqual(
            content_release_values.get(id=content_release.id),
            content_release_values.get(id=new_content_release.id),
        )

        # compare release_documents
        release_documents = content_release.release_documents.order_by(
            'id').values('id')
        new_release_documents = new_content_release.release_documents.order_by(
            'id').values('id')
        self.assertEqual(list(release_documents), list(new_release_documents))

        # compare extra_parameters
        extra_parameters = ContentReleaseExtraParameter.objects.filter(
            content_release=content_release,
        ).order_by('key').values('key', 'content',)
        new_extra_parameters = ContentReleaseExtraParameter.objects.filter(
            content_release=content_release,
        ).order_by('key').values('key', 'content',)
        self.assertEqual(list(extra_parameters), list(new_extra_parameters))

