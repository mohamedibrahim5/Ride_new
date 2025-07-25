from authentication.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from authentication.models import CarAvailability, CarRental
from threading import local

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
