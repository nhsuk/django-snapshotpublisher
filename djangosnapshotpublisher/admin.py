"""
.. module:: djangosnapshotpublisher.admin
   :synopsis: djangosnapshotpublisher custom django admin
"""
from django.contrib import admin

from .models import ContentRelease, ReleaseDocument


class ContentReleaseAdmin(admin.ModelAdmin):
    """ ContentReleaseAdmin """
    ordering = ['title']
    list_display = ('title', 'version', 'site_code', 'uuid', 'base_release', )
    list_filter = ('site_code', )
    readonly_fields = ['base_release']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['base_release']
        else:
            return []

admin.site.register(ContentRelease, ContentReleaseAdmin)
admin.site.register(ReleaseDocument)
