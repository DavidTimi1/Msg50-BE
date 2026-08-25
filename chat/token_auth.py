from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get("access_token")
        if access_token is None:
            return None

        validated_token = self.get_validated_token(access_token)
        return self.get_user(validated_token), validated_token

    def authenticate_header(self, request):
        return 'Cookie'


from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.db import close_old_connections
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from drf_spectacular.utils import extend_schema

from chat.serializers import (
    CustomTokenObtainPairSerializer, 
    LoginRequestSerializer, 
    AuthSuccessSerializer,
    SimpleSuccessResponseSerializer
)
from chat.throttling import AuthRateThrottle
from e2ee_chatapp.settings import DEBUG, SAME_SITE
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from random import choices
from string import ascii_lowercase, digits

User = get_user_model()


class TokenAuthMiddleware(BaseMiddleware):
    """Middleware to authenticate users via HttpOnly token in WebSockets."""

    async def __call__(self, scope, receive, send):
        if ("user" not in scope) or not (getattr(scope["user"], "is_authenticated", False)):
            scope["user"] = await self.get_user(scope)

        close_old_connections()
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, scope):
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode()
        cookies = {cookie.split("=")[0]: cookie.split("=")[1] for cookie in cookie_header.split("; ") if "=" in cookie}
        token = cookies.get("access_token")

        if not token:
            return AnonymousUser()
        
        try: 
            access_token = AccessToken(token)
            user = User.objects.get(id=access_token["user_id"])
            return user
        except Exception:
            return AnonymousUser()


class CookieTokenObtainPairView(TokenObtainPairView):
    """Authenticate with username and password, receiving HttpOnly auth cookies."""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="User Login (Obtain Auth Cookies)",
        description="Authenticates username/password and sets HttpOnly access_token and refresh_token cookies.",
        request=LoginRequestSerializer,
        responses={200: CustomTokenObtainPairSerializer, 401: SimpleSuccessResponseSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        access_token = response.data.get('access')
        refresh_token = response.data.get('refresh')

        if not access_token or not refresh_token:
            return response 

        setCookies(response, access_token, refresh_token)

        del response.data['access']
        del response.data['refresh']
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """Refresh JWT access token cookie using HttpOnly refresh token cookie."""
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Refresh Auth Token Cookie",
        description="Reads refresh_token cookie and sets a new access_token HttpOnly cookie.",
        request=None,
        responses={200: SimpleSuccessResponseSerializer, 401: SimpleSuccessResponseSerializer}
    )
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({'detail': 'Refresh token missing'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={'refresh': refresh_token})

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({'detail': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

        access_token = serializer.validated_data.get('access')

        response = Response()
        setCookies(response, access_token)
        response.data = {'detail': 'Access token refreshed successfully'}
        return response


class CookieTokenVerifyView(TokenVerifyView):
    """Verify access token cookie validity."""
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Verify Access Token Cookie",
        description="Validates active access_token HttpOnly cookie.",
        request=None,
        responses={200: SimpleSuccessResponseSerializer, 401: SimpleSuccessResponseSerializer}
    )
    def post(self, request, *args, **kwargs):
        access_token = request.COOKIES.get('access_token')

        if not access_token:
            return Response({'detail': 'Access token missing'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={'token': access_token})

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({'detail': 'Invalid or expired token'}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({'detail': 'Token is valid'})


class CookieGuestLoginView(APIView):
    """Log in as a passwordless guest user."""
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Guest User Login",
        description="Creates an anonymous temporary guest user account and sets HttpOnly auth cookies.",
        request=None,
        responses={200: AuthSuccessSerializer}
    )
    def post(self, request):
        random_username = "guest_" + ''.join(choices(ascii_lowercase + digits, k=8))

        guest_user = User.objects.create_user(
            username=random_username,
            password=None,
            is_guest=True
        )
        guest_user.is_active = True
        guest_user.save()

        refresh = RefreshToken.for_user(guest_user)
        access_token = str(refresh.access_token)

        response = Response({
            "message": "Guest login successful",
            "username": guest_user.username,
            "user_id": str(guest_user.id),
        }, status=status.HTTP_200_OK)

        setCookies(response, access_token, refresh)
        return response


def setCookies(response, access=None, refresh=None):
    if access:
        response.set_cookie(
            key='access_token',
            value=access,
            httponly=True,
            secure=True,
            samesite=SAME_SITE,
            max_age=60*60*24*3
        )

    if refresh:
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite=SAME_SITE,
            max_age=60*60*24*7
        )
