"""
.. module:: djangosnapshotpublisher.admin
   :synopsis: djangosnapshotpublisher custom django admin
"""
from django.contrib import admin

from .models import (ContentRelease, ContentReleaseExtraParameter, ReleaseDocument,
                     ReleaseDocumentExtraParameter)


class ContentReleaseExtraParameterInline(admin.TabularInline):
    """ ContentReleaseExtraParameterInline """
    model = ContentReleaseExtraParameter


class ContentReleaseAdmin(admin.ModelAdmin):
    """ ContentReleaseAdmin """
    ordering = ['title']
    list_display = ('title', 'version', 'site_code', 'uuid', 'base_release', )
    list_filter = ('site_code', )
    readonly_fields = ['base_release']
    inlines = [
        ContentReleaseExtraParameterInline,
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['base_release']
        else:
            return []

admin.site.register(ContentRelease, ContentReleaseAdmin)


class ReleaseDocumentExtraParameterInline(admin.TabularInline):
    """ ReleaseDocumentExtraParameterInline """
    model = ReleaseDocumentExtraParameter


class ReleaseDocumentAdmin(admin.ModelAdmin):
    """ ReleaseDocumentAdmin """
    ordering = ['content_type', 'document_key']
    list_display = ('content_type', 'document_key', 'deleted',)
    list_filter = ('content_type', 'content_releases', 'document_key',)
    inlines = [
        ReleaseDocumentExtraParameterInline,
    ]


admin.site.register(ReleaseDocument, ReleaseDocumentAdmin)
