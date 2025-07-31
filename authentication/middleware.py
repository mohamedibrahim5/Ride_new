from django.utils.deprecation import MiddlewareMixin
from django.contrib import admin
from .models import PlatformSettings

class DashboardSettingsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            settings = PlatformSettings.objects.first()
            if settings:
                admin.site.site_header = settings.platform_name
                admin.site.site_title = settings.platform_name
                admin.site.index_title = settings.platform_name
            else:
                admin.site.site_header = 'Ride Store Dashboard'
                admin.site.site_title = 'Ride Store Dashboard'
                admin.site.index_title = 'Ride Store Dashboard'
        except:
            pass  # Handle case where database is not ready