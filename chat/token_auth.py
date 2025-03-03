from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from django.db import close_old_connections
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


class TokenAuthMiddleware(BaseMiddleware):
    """Middleware to authenticate users via token in WebSockets."""

    async def __call__(self, scope, receive, send):
        """Process WebSocket authentication before connection."""

        if ("user" not in scope) or not (getattr(scope["user"], "is_authenticated", False)):
            scope["user"] = await self.get_user(scope)

        close_old_connections()
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, scope):
        """ Vaidates JWT token and returns the user object if valid """
        query_string = scope["query_string"].decode()  # Extract query parameters
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if not token:
            return AnonymousUser()
        
        try: 
            access_token = AccessToken(token)
            user = User.objects.get(id=access_token["user_id"]) # Get user from db
            return user

        except Exception:
            return AnonymousUser()
