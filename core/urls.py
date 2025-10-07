from django.urls import path, re_path
from . import views

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('quick-actions/', views.quick_actions, name='quick_actions'),
    # .well-known endpoints for app/universal links
    re_path(r'^\.well-known/apple-app-site-association$', views.apple_app_site_association, name='apple-app-site-association'),
    re_path(r'^\.well-known/assetlinks\.json$', views.android_assetlinks, name='android-assetlinks'),
] 