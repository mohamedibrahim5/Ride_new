from authentication.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from authentication.models import CarAvailability, CarRental, Provider, DriverProfile, PlatformSettings
from threading import local
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import os, shutil


_thread_locals = local()

def set_request_data(data):
    _thread_locals.request_data = data

def get_request_data():
    return getattr(_thread_locals, 'request_data', None)

@receiver(post_save, sender=User)
def create_token(sender, **kwargs):
    created = kwargs["created"]
    instance = kwargs["instance"]
    if created:
        Token.objects.create(user=instance)
        
        
@receiver([post_save, post_delete], sender=CarAvailability)
@receiver([post_save, post_delete], sender=CarRental)
def update_car_availability(sender, instance, **kwargs):
    car = instance.car
    car.update_availability()


@receiver(post_save, sender=Provider)
def sync_driverprofile_is_verified(sender, instance, **kwargs):
    try:
        driver_profile = instance.driver_profile
        if driver_profile.is_verified != instance.is_verified:
            driver_profile.is_verified = instance.is_verified
            driver_profile.save(update_fields=["is_verified"])
    except DriverProfile.DoesNotExist:
        pass 
    
import logging

# Set up logging
logger = logging.getLogger(__name__)
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

# Temporary store for original logo paths
_original_logos = {}

@receiver(pre_save, sender=PlatformSettings)
def cache_original_logo(sender, instance, **kwargs):
    if instance.pk:
        try:
            original = PlatformSettings.objects.get(pk=instance.pk)
            _original_logos[instance.pk] = original.platform_logo.path if original.platform_logo else None
        except PlatformSettings.DoesNotExist:
            _original_logos[instance.pk] = None


@receiver(post_save, sender=PlatformSettings)
def update_logo(sender, instance, **kwargs):
    import os, shutil
    from django.conf import settings

    static_logo_dir = os.path.join(settings.MEDIA_ROOT, 'dashboard_logos')
    static_logo_path = os.path.join(static_logo_dir, 'logo.png')
    os.makedirs(static_logo_dir, exist_ok=True)

    original_logo_path = _original_logos.pop(instance.pk, None)

    # If new logo is uploaded
    if instance.platform_logo:
        try:
            shutil.copy2(instance.platform_logo.path, static_logo_path)
            logger.info(f"Logo copied to {static_logo_path}")
        except Exception as e:
            logger.error(f"Failed to copy logo: {str(e)}")

    # If logo was cleared
    elif not instance.platform_logo and original_logo_path:
        try:
            if os.path.exists(static_logo_path):
                os.remove(static_logo_path)
                logger.info(f"Logo deleted from {static_logo_path}")
        except Exception as e:
            logger.error(f"Failed to delete logo: {str(e)}")
