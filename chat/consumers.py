from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message
import json


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        current_user = self.scope["user"]
        self.user_id = current_user.id

        print(current_user, self.user_id)

        if not current_user.is_authenticated:
            print("User is not authenticated")
            await self.close(400, "User is not authenticated")
            return

        self.group_name = f"chat_{self.user_id}"
        
        # Join the user's personal channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Check if the user has any queued messages
        queuedMessages = Message.objects.filter(receiver_id=self.user_id)

        for message in queuedMessages:
            await self.send(text_data=json.dumps({
                "action": "new_message",
                "receiver_id": message.receiver_id,
                "message": message.encrypted_message,
            }))

            message.delete() # clear each message after sending


    async def disconnect(self, close_code):
        if self.scope["user"].is_authenticated:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print("Closing connection", close_code)

    
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        receiver_id = data.get("receiver_id")
        message_id = data.get("message_id")
        encrypted_data = data.get("encrypted_data")
        
        print(data)
        
        message = {
            "action": "new_message",
            "encrypted_data": encrypted_data,
            "id": message_id
        }

        if action == "send_message":
            await self.send_message(receiver_id, message)

        elif action == "status_change":
            await self.send_status(receiver_id, message)


    async def send_message(self, receiver_id, message):
        if await self.is_online(receiver_id):
            await self.channel_layer.group_send(
                f"chat_{receiver_id}",
                {"type": "chat.message", "message": message}
            )

        else:
            Message.objects.create(
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
            Message.objects.create(
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

