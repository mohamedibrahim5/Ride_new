from authentication.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from authentication.models import CarAvailability, CarRental, Provider, DriverProfile, PlatformSettings, Customer
from threading import local
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import os, shutil
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from .models import RideStatus, Invoice


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


@receiver(post_save, sender=RideStatus)
def create_invoice_when_ride_finished(sender, instance, created, **kwargs):
    if instance.status == 'finished':
        # Check if invoice already exists
        if not hasattr(instance, 'invoice'):
            # Calculate values
            total = Decimal(instance.total_price or 0)
            tax = total * Decimal('0.1')  # 10% tax (you can customize this)
            discount = Decimal('0.0')     # or fetch from coupon if needed
            final = total + tax - discount

            Invoice.objects.create(
                ride=instance,
                total_amount=total,
                tax=tax,
                discount=discount,
                final_amount=final,
                issued_at=timezone.now(),
                status='unpaid',  # or 'paid' if logic determines it's already paid
                notes=f"Auto-generated for ride #{instance.pk}"
            )


@receiver(post_save, sender=RideStatus)
def handle_ride_status_change(sender, instance, **kwargs):
    if instance.status in ("finished", "cancelled"):
        _reset_flags(instance)

@receiver(post_delete, sender=RideStatus)
def handle_ride_deleted(sender, instance, **kwargs):
    _reset_flags(instance)

def _reset_flags(instance):
    # Reset customer in_ride
    try:
        customer = Customer.objects.get(user=instance.client)
        if customer.in_ride:
            customer.in_ride = False
            customer.save()
    except Customer.DoesNotExist:
        pass

    # Reset provider in_ride and driver status
    if instance.provider:
        try:
            provider = Provider.objects.get(user=instance.provider)
            if provider.in_ride:
                provider.in_ride = False
                provider.save()

            if hasattr(provider, "driver_profile"):
                driver = provider.driver_profile
                if driver.status != "available":
                    driver.status = "available"
                    driver.save()
        except Provider.DoesNotExist:
            pass