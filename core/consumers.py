import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from authentication.models import User, RideStatus, ProviderServicePricing
import math


def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the great-circle distance in kilometers between two points
        on the Earth specified by latitude and longitude.
        """
        R = 6371.0  # Radius of Earth in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)

        a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return round(R * c, 2)
    
    
class ApplyConsumer(AsyncWebsocketConsumer):
    connected_users = set()

    @database_sync_to_async
    def get_image(self, user, sender):
        data = {}
        if self.scope["user"]:
            image = self.scope["user"].image
            data["user_image"] = image
        if sender:
            user_sender = User.objects.get(phone=user)
            data["sender_image"] = user_sender.image
        return data


    async def connect(self):
        user_id = self.scope['user'].id
        await self.channel_layer.group_add(f'user_{user_id}', self.channel_name)
        self.connected_users.add(user_id)
        await self.accept()

    async def disconnect(self, close_code):
        user_id = self.scope['user'].id
        await self.channel_layer.group_discard(f'user_{user_id}', self.channel_name)
        self.connected_users.discard(user_id)

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

    @database_sync_to_async
    def lock_and_process_ride(self, client_id, provider_id, accepted):
        try:
            with transaction.atomic():
                ride = RideStatus.objects.select_for_update().filter(client_id=client_id).order_by('-created_at').first()

                if not ride:
                    return None  # No ride found

                if ride.status != "pending":
                    return None  # Already accepted or cancelled

                if accepted:
                    ride.provider_id = provider_id
                    ride.status = "accepted"
                    ride.save()
                    return "send_acceptance"
                else:
                    ride.status = "cancelled"
                    ride.save()
                    return "send_cancel"
        except RideStatus.DoesNotExist:
            return None
        

    @database_sync_to_async
    def get_provider_name(self, ride_id):
        """Get provider name for a ride"""
        try:
            ride = RideStatus.objects.select_related('provider').get(id=ride_id)
            if ride.provider:
                return ride.provider.name
            return None
        except Exception as e:
            print(f"[get_provider_name] Error: {e}")
            return None

    @database_sync_to_async
    def get_service_price_info(self, ride_id):
        try:
            ride = RideStatus.objects.select_related('provider', 'service').get(id=ride_id)

            if ride.service:
                # Get provider's sub_service if available
                sub_service = None
                if ride.provider and hasattr(ride.provider, 'provider'):
                    sub_service = ride.provider.provider.sub_service
                
                # Use location-based pricing
                pricing = ProviderServicePricing.get_pricing_for_location(
                    service=ride.service,
                    sub_service=sub_service,
                    lat=ride.pickup_lat,
                    lng=ride.pickup_lng
                )

                if pricing:
                    # Calculate distance in KM using pickup and drop coordinates
                    if all([ride.pickup_lat, ride.pickup_lng, ride.drop_lat, ride.drop_lng]):
                        distance_km = haversine_distance(
                            ride.pickup_lat, ride.pickup_lng, ride.drop_lat, ride.drop_lng
                        )
                        # Estimate duration (assuming average speed of 30 km/h in city)
                        duration_minutes = (distance_km / 30) * 60
                    else:
                        distance_km = 0
                        duration_minutes = 0

                    # Use pricing calculation method
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


    # Generic JSON sender
    async def send_json(self, event):
        # If the event contains a ride_id, try to add service_price_info and provider name
        data = event.get("data", {})
        ride_id = data.get("ride_id") or data.get("id")
        
        if event.get("type") in [
            "send_acceptance",
            "send_new_ride",
            "send_cash",
            "ride_status_update",
        ] and ride_id:
            # Get pricing info
            price_info = await self.get_service_price_info(ride_id)
            if price_info is not None:
                data["service_price_info"] = price_info
            
            # Get provider name for status updates
            if event.get("type") == "ride_status_update":
                provider_name = await self.get_provider_name(ride_id)
                if provider_name:
                    data["provider_name"] = provider_name
            
            event["data"] = data

        await self.send(text_data=json.dumps({
            "type": event["type"],
            "data": event["data"]
        }, ensure_ascii=False))

    # Event-specific senders
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
            print(f"[RECEIVE] Raw text_data: {text_data}")
            if not data:
                print("[RECEIVE] No data found in message.")
                return

            msg_type = data.get("type")
            print(f"[RECEIVE] Message type: {msg_type}, Data: {data}")

            if msg_type == "location_update":
                location = data.get("location")
                heading = data.get("heading")
                print(f"[LOCATION_UPDATE] Received location: {location}, heading: {heading}")

                if location:
                    await self.update_location(location=location)
                    print(f"[LOCATION_UPDATE] Updated location for user {self.scope['user'].id}: {location}")

                    ride = await database_sync_to_async(
                        lambda: RideStatus.objects.filter(
                            provider_id=self.scope["user"].id,
                            status="accepted"
                        ).first()
                    )()

                    if ride:
                        client_id = ride.client_id
                        print(f"[LOCATION_UPDATE] Found accepted ride. Sending location to client {client_id} in group user_{client_id}")
                        await self.channel_layer.group_send(
                            f"user_{client_id}",
                            {
                                "type": "location",
                                "location": location,
                                "heading": heading,
                            }
                        )
                        print(f"[LOCATION_UPDATE] Location sent to group user_{client_id}")
                    else:
                        print(f"[LOCATION_UPDATE] No accepted ride found for provider {self.scope['user'].id}")
                        await self.send_json({
                            "type": "no_accepted_ride",
                            "data": {
                                "message": "No accepted ride found for this provider."
                            }
                        })

            elif msg_type == "provider_response":
                client_id = data.get("client_id")
                accepted = data.get("accepted")
                print(f"[PROVIDER_RESPONSE] client_id: {client_id}, accepted: {accepted}")

                if client_id is None or accepted is None:
                    print("[PROVIDER_RESPONSE] Missing client_id or accepted in provider_response")
                    return

                event_type = await self.lock_and_process_ride(
                    client_id=client_id,
                    provider_id=self.scope["user"].id,
                    accepted=accepted
                )
                print(f"[PROVIDER_RESPONSE] lock_and_process_ride returned event_type: {event_type}")

                if event_type:
                    print(f"[PROVIDER_RESPONSE] Sending {event_type} to user_{client_id}")
                    ride = await database_sync_to_async(
                        lambda: RideStatus.objects.filter(client_id=client_id).order_by('-created_at').first()
                    )()
                    
                    # Get provider name
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
                    print(f"[PROVIDER_RESPONSE] {event_type} sent to group user_{client_id}")
                else:
                    print("[PROVIDER_RESPONSE] Ride was already handled or not found.")
                    await self.send_json({
                        "type": "ride_already_handled",
                        "data": {
                            "client_id": client_id,
                            "message": "This ride has already been accepted or cancelled."
                        }
                    })
        except Exception as e:
            print("[RECEIVE] WebSocket receive error:", e)
