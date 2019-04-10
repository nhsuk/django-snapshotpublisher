from django.core.management.base import BaseCommand

from djangosnapshotpublisher.models import ContentRelease
from djangosnapshotpublisher.publisher_api import PublisherAPI


class Command(BaseCommand):
    help = 'Publish schedule ContentRelease'

    def handle(self, *args, **options):
        site_codes = ContentRelease.objects.values_list('site_code', flat=True).distinct()
        for site_code in site_codes:
            publisher_api = PublisherAPI(api_type='django')
            publisher_api.get_live_content_release(site_code)