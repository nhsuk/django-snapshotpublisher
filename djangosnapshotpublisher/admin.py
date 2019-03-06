from django.contrib import admin

from .models import ContentRelease, ReleaseDocument


class ContentReleaseAdmin(admin.ModelAdmin):
    ordering = ['title']
    list_display = ('title', 'version', 'site_code', 'uuid', 'base_release', )
    list_filter = ('site_code', )


admin.site.register(ContentRelease, ContentReleaseAdmin)
admin.site.register(ReleaseDocument)