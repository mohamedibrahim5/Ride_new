from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import path, include
from project.admin import admin
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _  

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # for language switching
    path("", lambda request: HttpResponse(_("Welcome to the Riders API")), name="welcome-page"),
    path("authentication/", include("authentication.urls")),


    
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    prefix_default_language=True  # optional, to not prefix default language
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
