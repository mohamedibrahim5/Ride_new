import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from authentication.models import User, RideStatus


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
                ride = RideStatus.objects.select_for_update().get(client_id=client_id)

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

    # Generic JSON sender
    async def send_json(self, event):
        await self.send(text_data=json.dumps({
            "type": event["type"],
            "data": event["data"]
        }))

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
        }))

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if not data:
                return

            msg_type = data.get("type")
            print("WebSocket message:", data)

            if msg_type == "location_update":
                location = data.get("location")
                heading = data.get("heading")

                if location:
                    await self.update_location(location=location)

                    ride = await database_sync_to_async(
                        lambda: RideStatus.objects.filter(
                            provider_id=self.scope["user"].id,
                            status="accepted"
                        ).first()
                    )()

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

            elif msg_type == "provider_response":
                client_id = data.get("client_id")
                accepted = data.get("accepted")

                if client_id is None or accepted is None:
                    print("Missing client_id or accepted in provider_response")
                    return

                event_type = await self.lock_and_process_ride(
                    client_id=client_id,
                    provider_id=self.scope["user"].id,
                    accepted=accepted
                )

                if event_type:
                    await self.channel_layer.group_send(
                        f"user_{client_id}",
                        {
                            "type": event_type,
                            "data": {
                                "provider_id": self.scope['user'].id,
                                "accepted": accepted
                            }
                        }
                    )
                else:
                    print("Ride was already handled or not found.")
        except Exception as e:
            print("WebSocket receive error:", e)
