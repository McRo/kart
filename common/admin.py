from django.contrib import admin

from .models import Website, BTBeacon


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('url', 'title_fr', 'language')
    search_fields = ['url', 'title_fr', 'language']


admin.site.register(BTBeacon)
