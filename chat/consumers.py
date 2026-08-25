import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

from .models import Message
from .redis_client import redis_client

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Authenticate user via WebSocket token."""
        current_user = self.scope.get("user", None)

        if not current_user or not current_user.is_authenticated:
            logger.warning("WebSocket connect attempt rejected: User is not authenticated")
            await self.close(400, "User is not authenticated")
            return
        
        self.user_id = current_user.id
        self.group_name = f"chat_{self.user_id}"

        if redis_client:
            try:
                await redis_client.set(
                    f"user_online:{str(self.user_id)}",
                    "1",
                    ex=60
                )
            except Exception as e:
                logger.error(f"Redis error on connect for user {self.user_id}: {e}")

        # Join the user's personal channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        current_user = self.scope.get("user", None)

        if current_user and current_user.is_authenticated and hasattr(self, 'user_id'):
            if redis_client:
                try:
                    await redis_client.delete(f"user_online:{str(self.user_id)}")
                except Exception as e:
                    logger.error(f"Redis error on disconnect for user {self.user_id}: {e}")
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            json_payload: dict = json.loads(text_data or bytes_data or "{}")
        except Exception:
            return

        # Ping-pong heartbeat
        if json_payload.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        action = json_payload.get("action")
        receiver_id = json_payload.get("receiverID")
        msg_id = json_payload.get("id")
        encrypted_data = json_payload.get("data")

        if action == "ready":
            await self.read_messages(self.user_id)
            return

        # Multi-recipient broadcast action
        if action == "broadcast":
            keys = json_payload.get("keys", {})
            for rec_id, enc_key in keys.items():
                recipient_msg_data = {
                    "iv": encrypted_data.get("iv"),
                    "encryptedData": encrypted_data.get("encryptedData"),
                    "key": enc_key,
                    "file": encrypted_data.get("file")
                }
                msg_item = {"id": msg_id, "data": recipient_msg_data}
                await self.send_message(rec_id, msg_item, "new-message")
            return

        # Typing indicator relay
        if action == "typing" and receiver_id:
            is_typing = json_payload.get("isTyping", True)
            if is_typing:
                await self.start_typing(self.user_id, receiver_id)
            else:
                await self.stop_typing(self.user_id, receiver_id)

            if await self.is_online(receiver_id):
                await self.channel_layer.group_send(
                    f"chat_{receiver_id}",
                    {
                        "type": "chat.typing",
                        "message": {
                            "type": "typing-status",
                            "senderID": str(self.user_id),
                            "isTyping": is_typing
                        }
                    }
                )
            return

        # Status ACK relay (Sent, Delivered, Read)
        if (action in ["status-ack", "status-change"]) and receiver_id:
            status_val = json_payload.get("status", "d")
            status_message = {
                "action": "status",
                "message_id": msg_id,
                "status": status_val,
                "senderID": str(self.user_id)
            }
            await self.send_status(receiver_id, {"id": msg_id, "data": status_message})
            return

        # Single recipient direct message
        if action == "new-message" and receiver_id:
            message = {"data": encrypted_data, "id": msg_id}
            await self.send_message(receiver_id, message, action)

    async def send_message(self, receiver_id, message, action, saved=False):
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

    async def send_status(self, receiver_id, message, saved=False):
        status_message = {"action": "status", "message_id": message["id"], "data": message.get("data")}

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

    async def chat_status(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    async def is_online(self, user_id):
        if not redis_client:
            return False
        try:
            return bool(await redis_client.exists(f"user_online:{str(user_id)}"))
        except Exception as e:
            logger.error(f"Redis is_online check failed for user {user_id}: {e}")
            return False

    async def start_typing(self, user_id, receiver_id):
        if redis_client:
            try:
                await redis_client.set(f"typing:{str(user_id)}:{str(receiver_id)}", "1", ex=5)
            except Exception:
                pass

    async def stop_typing(self, user_id, receiver_id):
        if redis_client:
            try:
                await redis_client.delete(f"typing:{str(user_id)}:{str(receiver_id)}")
            except Exception:
                pass

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
            logger.error(f"Failed to delete message {msg_id}: {err}")

    @database_sync_to_async
    def store_message(self, **params):
        Message.objects.create(**params)
