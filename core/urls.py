from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('quick-actions/', views.quick_actions, name='quick_actions'),
] 