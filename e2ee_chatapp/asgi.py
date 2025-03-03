"""
ASGI config for e2ee_chatapp project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e2ee_chatapp.settings')
django.setup()  # Ensures Django is properly loaded before ASGI starts


from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from chat.ws_urls import websocket_urlpatterns
from chat.token_auth import TokenAuthMiddleware



application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        TokenAuthMiddleware(        
            URLRouter(websocket_urlpatterns)
        )
    ),
})

