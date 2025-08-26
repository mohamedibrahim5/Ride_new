from celery import shared_task
from django.utils import timezone
from django.db import transaction

from authentication.models import ScheduledRide, RideStatus
from authentication.utils import create_notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task
def start_scheduled_ride(scheduled_ride_id: int) -> None:
    try:
        sr = ScheduledRide.objects.select_related('client', 'provider', 'service').get(id=scheduled_ride_id)
    except ScheduledRide.DoesNotExist:
        return

    if sr.status != ScheduledRide.STATUS_ACCEPTED:
        return

    if sr.scheduled_time > timezone.now():
        # Too early; requeue shortly just in case of clock skew
        start_scheduled_ride.apply_async((scheduled_ride_id,), countdown=30)
        return

    with transaction.atomic():
        ride = RideStatus.objects.create(
            client=sr.client,
            provider=sr.provider,
            service=sr.service,
            status="accepted",
            pickup_lat=sr.pickup_lat,
            pickup_lng=sr.pickup_lng,
            drop_lat=sr.drop_lat,
            drop_lng=sr.drop_lng,
        )
        sr.status = ScheduledRide.STATUS_STARTED
        sr.save(update_fields=["status"])

        # Mark provider in ride
        provider_profile = getattr(sr.provider, 'provider', None)
        if provider_profile:
            provider_profile.in_ride = True
            provider_profile.save(update_fields=["in_ride"])
            if hasattr(provider_profile, 'driver_profile'):
                provider_profile.driver_profile.status = 'in_ride'
                provider_profile.driver_profile.save(update_fields=["status"])

    # Notify both parties
    create_notification(
        user=sr.client,
        title="Scheduled Ride Started",
        message="Your scheduled ride has started.",
        notification_type='ride_status',
        data={'ride_id': ride.id}
    )
    create_notification(
        user=sr.provider,
        title="Scheduled Ride Started",
        message="The scheduled ride has started.",
        notification_type='ride_status',
        data={'ride_id': ride.id}
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{sr.client.id}",
        {"type": "ride_status_update", "data": {"status": "accepted", "ride_id": ride.id}}
    )
    async_to_sync(channel_layer.group_send)(
        f"user_{sr.provider.id}",
        {"type": "ride_status_update", "data": {"status": "accepted", "ride_id": ride.id}}
    )




# add task to send notification and socket to client and provider in same day the ride must start
@shared_task
def send_notification_and_socket_to_client_and_provider(scheduled_ride_id: int) -> None:
    print("send notification and socket to client and provider triggered")
    try:
        sr = ScheduledRide.objects.select_related('client', 'provider', 'service').get(id=scheduled_ride_id)
    except ScheduledRide.DoesNotExist:
        return

    if sr.status != ScheduledRide.STATUS_ACCEPTED:
        return

    now = timezone.now()

    # If it's exactly noon local time, or the ride is today, notify both sides
    is_noon = now.hour == 12 and now.minute == 0
    is_same_day = sr.scheduled_time.astimezone(now.tzinfo).date() == now.date()

    if is_noon or is_same_day:
        create_notification(
            user=sr.client,
            title="Scheduled Ride Reminder",
            message="Your scheduled ride is today.",
            notification_type='ride_status',
            data={'scheduled_ride_id': sr.id}
        )
        create_notification(
            user=sr.provider,
            title="Scheduled Ride Reminder",
            message="You have a scheduled ride today.",
            notification_type='ride_status',
            data={'scheduled_ride_id': sr.id}
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{sr.client.id}",
            {"type": "ride_status_update", "data": {"type": "scheduled_ride_reminder", "scheduled_ride_id": sr.id}}
        )
        async_to_sync(channel_layer.group_send)(
            f"user_{sr.provider.id}",
            {"type": "ride_status_update", "data": {"type": "scheduled_ride_reminder", "scheduled_ride_id": sr.id}}
        )