import json
import math
import asyncio
from functools import wraps
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from authentication.models import User, RideStatus, ProviderServicePricing


# Timeout decorator for async functions
def with_timeout(seconds=5):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                print(f"[TIMEOUT] Function `{func.__name__}` timed out after {seconds} seconds.")
                return None
        return wrapper
    return decorator


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


class ApplyConsumer(AsyncWebsocketConsumer):
    connected_users = set()

    async def connect(self):
        self.bg_tasks = []
        user_id = self.scope['user'].id
        await self.channel_layer.group_add(f'user_{user_id}', self.channel_name)
        self.connected_users.add(user_id)
        await self.accept()

    async def disconnect(self, close_code):
        user_id = self.scope['user'].id
        try:
            await self.channel_layer.group_discard(f'user_{user_id}', self.channel_name)
        except Exception as e:
            print(f"[DISCONNECT] Error discarding group: {e}")
        self.connected_users.discard(user_id)
        for task in getattr(self, "bg_tasks", []):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @database_sync_to_async
    def get_image(self, user, sender):
        data = {}
        try:
            if self.scope["user"]:
                data["user_image"] = self.scope["user"].image
            if sender:
                data["sender_image"] = User.objects.get(phone=user).image
        except User.DoesNotExist:
            data["sender_image"] = None
        return data

    @database_sync_to_async
    def update_location(self, location):
        try:
            if isinstance(location, str) and ',' in location:
                lat_str, lng_str = location.split(',')
                lat, lng = float(lat_str.strip()), float(lng_str.strip())
                return User.objects.filter(id=self.scope['user'].id).update(
                    location=location, location2_lat=lat, location2_lng=lng
                )
            return User.objects.filter(id=self.scope['user'].id).update(location=location)
        except Exception as e:
            print(f"Error updating location: {e}")
            return None

    @with_timeout(5)
    @database_sync_to_async
    def lock_and_process_ride(self, client_id, provider_id, accepted):
        try:
            with transaction.atomic():
                ride = RideStatus.objects.select_for_update().filter(client_id=client_id).order_by('-created_at').first()
                if not ride or ride.status != "pending":
                    return None
                ride.provider_id = provider_id
                ride.status = "accepted" if accepted else "cancelled"
                ride.save()
                return "send_acceptance" if accepted else "send_cancel"
        except RideStatus.DoesNotExist:
            return None

    @with_timeout(5)
    @database_sync_to_async
    def get_provider_name(self, ride_id):
        try:
            ride = RideStatus.objects.select_related('provider').get(id=ride_id)
            return ride.provider.name if ride.provider else None
        except Exception as e:
            print(f"[get_provider_name] Error: {e}")
            return None

    @with_timeout(5)
    @database_sync_to_async
    def get_service_price_info(self, ride_id):
        try:
            ride = RideStatus.objects.select_related('provider', 'service').get(id=ride_id)
            if ride.service:
                sub_service = None
                if ride.provider and hasattr(ride.provider, 'provider'):
                    sub_service = ride.provider.provider.sub_service
                pricing = ProviderServicePricing.get_pricing_for_location(
                    service=ride.service,
                    sub_service=sub_service,
                    lat=ride.pickup_lat,
                    lng=ride.pickup_lng
                )
                if pricing:
                    distance_km = duration_minutes = 0
                    if all([ride.pickup_lat, ride.pickup_lng, ride.drop_lat, ride.drop_lng]):
                        distance_km = haversine_distance(
                            ride.pickup_lat, ride.pickup_lng, ride.drop_lat, ride.drop_lng
                        )
                        duration_minutes = (distance_km / 30) * 60
                    total_price = pricing.calculate_price(
                        distance_km=distance_km,
                        duration_minutes=duration_minutes,
                        pickup_time=ride.created_at
                    )
                    return {
                        "base_fare": float(pricing.base_fare),
                        "price_per_km": float(pricing.price_per_km),
                        "price_per_minute": float(pricing.price_per_minute),
                        "platform_fee": float(pricing.platform_fee or 0),
                        "service_fee": float(pricing.service_fee or 0),
                        "booking_fee": float(pricing.booking_fee or 0),
                        "distance_km": distance_km,
                        "duration_minutes": round(duration_minutes, 2),
                        "total_price": total_price,
                        "zone_name": pricing.zone.name if pricing.zone else "Default",
                        "minimum_fare": float(pricing.minimum_fare),
                        "peak_multiplier": float(pricing.peak_hour_multiplier),
                    }
            return None
        except Exception as e:
            print(f"[get_service_price_info] Error: {e}")
            return None

    @with_timeout(5)
    @database_sync_to_async
    def get_accepted_ride(self):
        return RideStatus.objects.filter(
            provider_id=self.scope["user"].id,
            status="accepted"
        ).first()

    @with_timeout(5)
    @database_sync_to_async
    def get_latest_ride_by_client(self, client_id):
        return RideStatus.objects.filter(client_id=client_id).order_by('-created_at').first()

    async def send_json(self, event):
        data = event.get("data", {})
        ride_id = data.get("ride_id") or data.get("id")
        if event.get("type") in ["send_acceptance", "send_new_ride", "send_cash", "ride_status_update"] and ride_id:
            price_info = await self.get_service_price_info(ride_id)
            if price_info:
                data["service_price_info"] = price_info
            if event.get("type") == "ride_status_update":
                provider_name = await self.get_provider_name(ride_id)
                if provider_name:
                    data["provider_name"] = provider_name
            event["data"] = data
        await self.send(text_data=json.dumps({
            "type": event["type"],
            "data": event["data"]
        }, ensure_ascii=False))

    async def location(self, event):
        await self.send(text_data=json.dumps({
            "type": "location",
            "data": {
                "location": event["location"],
                "heading": event["heading"]
            }
        }, ensure_ascii=False))

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")
            if msg_type == "location_update":
                location = data.get("location")
                heading = data.get("heading")
                if location:
                    await self.update_location(location=location)
                    ride = await self.get_accepted_ride()
                    if ride:
                        client_id = ride.client_id
                        await self.channel_layer.group_send(
                            f"user_{client_id}",
                            {
                                "type": "location",
                                "location": location,
                                "heading": heading,
                            }
                        )
                    else:
                        await self.send_json({
                            "type": "no_accepted_ride",
                            "data": {"message": "No accepted ride found for this provider."}
                        })
            elif msg_type == "provider_response":
                client_id = data.get("client_id")
                accepted = data.get("accepted")
                if client_id is None or accepted is None:
                    return
                event_type = await self.lock_and_process_ride(
                    client_id=client_id,
                    provider_id=self.scope["user"].id,
                    accepted=accepted
                )
                if event_type:
                    ride = await self.get_latest_ride_by_client(client_id)
                    provider_name = await self.get_provider_name(ride.id)
                    await self.channel_layer.group_send(
                        f"user_{client_id}",
                        {
                            "type": event_type,
                            "data": {
                                "ride_id": ride.id,
                                "provider_id": self.scope['user'].id,
                                "provider_name": provider_name,
                                "accepted": accepted
                            }
                        }
                    )
                else:
                    await self.send_json({
                        "type": "ride_already_handled",
                        "data": {
                            "client_id": client_id,
                            "message": "This ride has already been accepted or cancelled."
                        }
                    })
        except Exception as e:
            print("[RECEIVE] WebSocket receive error:", e)

    # Attach all send_* methods
    async def send_apply(self, event): await self.send_json(event)
    async def send_not(self, event): await self.send_json(event)
    async def send_acceptance(self, event): await self.send_json(event)
    async def send_cancel(self, event): await self.send_json(event)
    async def send_arrival(self, event): await self.send_json(event)
    async def send_done(self, event): await self.send_json(event)
    async def send_cancel_apply(self, event): await self.send_json(event)
    async def send_approval(self, event): await self.send_json(event)
    async def send_cash(self, event): await self.send_json(event)
    async def send_user(self, event): await self.send_json(event)
    async def send_new_ride(self, event): await self.send_json(event)
    async def ride_finished(self, event): await self.send_json(event)
    async def user_not_accept_cash(self, event): await self.send_json(event)
    async def fail_card(self, event): await self.send_json(event)
    async def send_client_cancel(self, event): await self.send_json(event)
    async def ride_status_update(self, event): await self.send_json(event)
Timeout decorators to auto-cancel stuck calls
