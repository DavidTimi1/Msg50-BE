import json
import string

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

from .models import Message


User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Authenticate user via WebSocket token."""
        current_user = self.scope.get("user", None)
        self.user_id = current_user.id

        if not current_user.is_authenticated:
            print("User is not authenticated")
            await self.close(400, "User is not authenticated")
            return

        self.group_name = f"chat_{self.user_id}"
        
        # Join the user's personal channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Check if the user has any queued messages
        await self.read_messages(self.user_id)


    async def disconnect(self, close_code):
        if self.scope["user"].is_authenticated:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print("Closing connection", close_code)

    
    async def receive(self, text_data):
        json_payload: dict = json.loads(text_data)
        action: string = json_payload.get("action")
        receiver_id: string = json_payload.get("receiverID")
        id: string = json_payload.get("id")
        encrypted_data: string = json_payload.get("data")
        
        message = {
            "encrypted_data": encrypted_data,
            "id": id
        }

        if action == "new-message":
            await self.send_message(receiver_id, message)

        elif action == "status-change":
            await self.send_status(receiver_id, message)


    async def send_message(self, receiver_id, message):
        print("Sending messsage to", receiver_id)

        if await self.is_online(receiver_id):
            await self.channel_layer.group_send(
                f"chat_{receiver_id}",
                {"type": "chat.message", "message": message}
            )

        else:
            print(receiver_id, "is not online, saving to database ...")
            await self.store_message(
                msg_id=message["id"],
                receiver_id=receiver_id,
                encrypted_message=message["encrypted_data"]
            )


    async def send_status(self, receiver_id, message):
        status_message = {"action": "status", "message_id": message["id"]}

        if await self.is_online(receiver_id):
            await self.channel_layer.group_send(
                f"chat_{receiver_id}",
                {"type": "chat.status", "message": status_message}
            )

        else:
            await self.store_message(
                msg_id=message["id"],
                receiver_id=receiver_id,
                encrypted_message=message["encrypted_data"],
                status=True
            )


    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))


    async def is_online(self, user_id):
        # This should check from an actual user online tracking system
        return user_id in [grp.split("_")[-1] for grp in self.channel_layer.groups]


    async def read_messages(self, user_id):
        queued_messages = await self.get_queued_messages(user_id)

        for message in queued_messages:
            print("A message for you!!")

            await self.send(text_data=json.dumps(message))
            await self.delete_message(message.id)


    @database_sync_to_async
    def get_queued_messages(self, user_id):
        queued_messages = Message.objects.filter(receiver_id=user_id)

        return [
            {
                "action": "new-message",
                "id": message.msg_id,
                "receiver_id": str(message.receiver_id),
                "message": message.encrypted_message,

            } for message in queued_messages
        ]


    @database_sync_to_async
    def delete_message(self, msg_id):
        try:
            msg = Message.objects.get(msg_id=msg_id)
            msg.delete()

        except:
            print("Did not find message")


    @database_sync_to_async
    def store_message(self, **params):
        Message.objects.create(**params)

