import json
from channels.generic.websocket import AsyncWebsocketConsumer
# from service.models import Apply
from channels.db import database_sync_to_async
import json
from authentication.models import User, RideStatus


class ApplyConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling apply-related events.

    Attributes:
        connected_users (set): A set of connected user IDs.

    Methods:
        get_image(user, sender): Retrieves the image associated with the user and sender.
        connect(): Connects the consumer to the WebSocket.
        disconnect(close_code): Disconnects the consumer from the WebSocket.
        update_location(location): Updates the location of the user.
        send_apply(event): Sends an apply event to the WebSocket.
        send_not(event): Sends a not event to the WebSocket.
        send_acceptance(event): Sends an acceptance event to the WebSocket.
        send_arrival(event): Sends an arrival event to the WebSocket.
        send_done(event): Sends a done event to the WebSocket.
        send_cancel(event): Sends a cancel event to the WebSocket.
        send_cancel_apply(event): Sends a cancel apply event to the WebSocket.
        send_approval(event): Sends an approval event to the WebSocket.
        send_cash(event): Sends a cash event to the WebSocket.
        send_user(event): Sends a user event to the WebSocket.
        receive(text_data): Receives data from the WebSocket.
        location(event): Sends a location event to the WebSocket.
        send_new_ride(event): Sends a new ride event to the WebSocket.
    """
    connected_users = set()

    @database_sync_to_async
    def get_image(self, user, sender):
        """
        Retrieves the image associated with the user and sender.

        Args:
            user (str): The phone number of the user.
            sender (bool): Indicates whether the sender's image should be retrieved.

        Returns:
            dict: A dictionary containing the user's image and, if specified, the sender's image.
        """
        data = {}

        if self.scope["user"]:
            image = self.scope["user"].image
        data["user_image"] = image
        if sender:
            user_sender = User.objects.get(phone=user)
            sender_image = user_sender.image
            data["sender_image"] = sender_image
        return data
    

    async def connect(self):
        user_id = self.scope['user'].id
        print(user_id)
        print(self.scope['user'])
        print('120120120',self.scope['user'].id)
        group_name = f'user_{user_id}'
        await self.channel_layer.group_add(
            group_name,
            self.channel_name
        )
        self.connected_users.add(user_id)
        print(self.connected_users)
        await self.accept()



    async def disconnect(self, close_code):
        user_id = self.scope['user'].id
        group_name = f'user_{user_id}'
        await self.channel_layer.group_discard(
            group_name,
            self.channel_name
        )
        self.connected_users.discard(user_id)

# --------------------------------------------------------------
# --------------------------------------------------------------
# --------------------------Events------------------------------
# --------------------------------------------------------------
# --------------------------------------------------------------

    @database_sync_to_async
    def update_location(self,location):
        user = User.objects.filter(id=self.scope['user'].id).update(location=location)
        
        return user
        
    

    async def send_apply(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))

    async def send_not(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))

    async def send_acceptance(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))
    # ride status update 
    async def ride_status_update(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))
    async def send_arrival(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))

    async def send_start_ride(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))


    async def send_done(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))


    async def send_cancel(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))


    async def send_cancel_apply(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))

    async def send_approval(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))

    async def send_cash(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))


    async def send_user(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))


    async def receive(self, text_data):
        data = json.loads(text_data)
        print('-----------------')
        print(data)
        print('-----------------')
        if not data:
            return
        msg_type = data.get("type")
        print('------------------------------------------------a7aa7a',msg_type)
        if msg_type == "provider_response":
            client_id = data["client_id"]
            accepted = data["accepted"]

            # Only process if ride is still pending
            ride = RideStatus.objects.filter(client_id=client_id, status="pending").first()
            if not ride:
                return  # Already processed

            if accepted:
                ride.provider_id = self.scope["user"].id
                ride.status = "accepted"
                ride.save()
            else:
                ride.status = "cancelled"
                ride.save()

            await self.channel_layer.group_send(
                f"user_{client_id}",
                {
                    "type": "send_acceptance" if accepted else "send_cancel",
                    "data": {
                        "provider_id": self.scope['user'].id,
                        "accepted": accepted,
                    },
                }
            )
        print(data)
        # user_id = data['user']
        # location = data.get('location')
        # heading = data.get('heading')

        # if location:
        #     location = data['location']
        #     print('aaaaaaaaaaaaaaaaa',await self.update_location(location=location,))
        #     if await self.update_location(location=location,):


        #         await self.channel_layer.group_send(
        #             f"user_{user_id}",
        #             {
        #                 "type": "location",
        #                 "location": location,
        #                 "heading": heading,
        #             },
        #         )

        #         await self.channel_layer.group_send(
        #             f"user_{self.scope['user'].id}",
        #             {
        #                 "type": "location",
        #                 "location": location,
        #                 "heading": heading,
        #             }
        #         )



    async def location(self, event):
        location = event["location"]
        heading = event["heading"]

        text_data = {
            "type": "location",
            "data": {
                "location": location,
                "heading": heading,
            },
        }

        await self.send(text_data=json.dumps(text_data))


    async def send_new_ride(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))
        

    async def ride_finished(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))   


    async def user_not_accept_cash(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))


    async def fail_card(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))


    async def send_client_cancel(self, event):
        text_data = {
            "type": event['type'],
            "data": event['data']
        }
        await self.send(text_data=json.dumps(text_data))
