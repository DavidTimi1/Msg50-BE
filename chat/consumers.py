from email import message
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

        if action == "ready":
            # Check if the user has any queued messages
            await self.read_messages(self.user_id)
            return
        
        message = {
            "data": encrypted_data,
            "id": id
        }

        if action == "new-message":
            await self.send_message(receiver_id, message, action)

        elif action == "status-change":
            await self.send_status(receiver_id, message, action)


    async def send_message(self, receiver_id, message, action, saved = False):
        if await self.is_online(receiver_id):
            await self.channel_layer.group_send(
                f"chat_{receiver_id}",
                {"type": "chat.message", "message": {"type": action, "data": message}}
            )
            return True

        elif not saved:
            await self.store_message(
                msg_id=message["id"],
                receiver_id=receiver_id,
                encrypted_message=message["data"]
            )
            
        return False


    async def send_status(self, receiver_id, message, saved = False):
        status_message = {"action": "status", "message_id": message["id"]}

        if await self.is_online(receiver_id):
            await self.channel_layer.group_send(
                f"chat_{receiver_id}",
                {"type": "chat.status", "message": status_message}
            )
            return True

        elif not saved:
            await self.store_message(
                msg_id=message["id"],
                receiver_id=receiver_id,
                encrypted_message=message["data"],
                status=True
            )

        return False


    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))


    async def is_online(self, user_id):
        # This should check from an actual user online tracking system
        return user_id in [grp.split("_")[-1] for grp in self.channel_layer.groups]


    async def read_messages(self, user_id):
        queued_messages = await self.get_queued_messages(user_id)

        for msg in queued_messages:
            action, message = msg
            sent = False

            if action == "new-message":
                sent = await self.send_message(user_id, message, action, True)

            elif action == "status-change":
                sent = await self.send_status(user_id, message, True)

            sent and await self.delete_message(message["id"], user_id)


    @database_sync_to_async
    def get_queued_messages(self, user_id):
        queued_messages = Message.objects.filter(receiver_id=user_id)

        return [
            ( "status-change" if message.status else "new-message", {
                "data": message.encrypted_message,
                "id": message.msg_id
            })
            for message in queued_messages
        ]


    @database_sync_to_async
    def delete_message(self, msg_id, rec_id):
        try:
            msg = Message.objects.get(msg_id=msg_id, receiver_id=rec_id)
            msg.delete()

        except Exception as err:
            print("Failed to delete message", err)


    @database_sync_to_async
    def store_message(self, **params):
        Message.objects.create(**params)
