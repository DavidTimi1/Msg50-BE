import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

from .models import Message
from .redis_client import redis_client


User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Authenticate user via WebSocket token."""
        current_user = self.scope.get("user", None)

        if not current_user or not current_user.is_authenticated:
            print("User is not authenticated")
            await self.close(400, "User is not authenticated")
            return
        
        self.user_id = current_user.id

        self.group_name = f"chat_{self.user_id}"
        await redis_client.set(
            f"user_online:{str(self.user_id)}",
            "1",
            ex=60
        )
        
        # Join the user's personal channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()


    async def disconnect(self, code):
        current_user = self.scope.get("user", None)

        if current_user and current_user.is_authenticated:
            await redis_client.delete(f"user_online:{str(self.user_id)}")
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        
        print("Closing connection", code)

    
    async def receive(self, text_data=None, bytes_data=None):
        json_payload: dict = json.loads(text_data or bytes_data or "{}")
        action = json_payload.get("action")
        receiver_id = json_payload.get("receiverID")
        id = json_payload.get("id")
        encrypted_data = json_payload.get("data")

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
            await self.send_status(receiver_id, message)


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
        return bool(await redis_client.exists(f"user_online:{str(user_id)}"))

    async def start_typing(self, user_id, receiver_id):
        await redis_client.set(f"typing:{str(user_id)}:{str(receiver_id)}", "1", ex=5)

    async def stop_typing(self, user_id, receiver_id):
        await redis_client.delete(f"typing:{str(user_id)}:{str(receiver_id)}")

    async def is_typing(self, user_id, receiver_id):
        return bool(await redis_client.exists(f"typing:{str(user_id)}:{str(receiver_id)}"))

    async def read_messages(self, user_id):
        queued_messages = await self.get_queued_messages(user_id)

        for msg in queued_messages:
            action, message = msg
            sent = False

            if action == "new-message":
                sent = await self.send_message(user_id, message, action, True)

            elif action == "status-change":
                sent = await self.send_status(user_id, message, True)

            if sent:
                await self.delete_message(message["id"], user_id)


    @database_sync_to_async
    def get_queued_messages(self, user_id):
        # Use values_list to avoid instantiating full model objects and limit batch size
        qs = (
            Message.objects
            .filter(receiver_id=user_id)
            .order_by('created_at')
            .values_list('status', 'encrypted_message', 'msg_id')[:100]
        )

        return [
            ("status-change" if status else "new-message", {"data": encrypted_message, "id": msg_id})
            for status, encrypted_message, msg_id in qs
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
