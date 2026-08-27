import json
import os
import random
from string import ascii_lowercase, digits
import uuid

from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from chat.token_auth import CookieJWTAuthentication
from chat.throttling import MediaUploadRateThrottle, PublicKeyRateThrottle, AuthRateThrottle
from chat.services.media_service import MediaService

from .serializers import (
    UserSerializer, 
    PublicUserSerializer,
    MessageSerializer, 
    RegisterSerializer,
    UserPublicKeySetSerializer,
    UserProfileEditSerializer,
    UserProfileEditResponseSerializer,
    MediaUploadSerializer,
    MediaUploadResponseSerializer,
    UserSettingsSerializer,
    SimpleSuccessResponseSerializer
)
from .models import Message, Media

from django.contrib.auth import get_user_model

User = get_user_model()


class MediaAccessView(APIView):
    """Access uploaded encrypted media files."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Retrieve or stream encrypted media file",
        description="Serve encrypted media blob or metadata by UUID if caller is authorized in recipient list.",
        parameters=[
            OpenApiParameter("metadata", OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Set to true to retrieve JSON metadata instead of binary blob", required=False)
        ],
        responses={
            200: OpenApiTypes.BINARY,
            403: SimpleSuccessResponseSerializer,
            404: SimpleSuccessResponseSerializer
        }
    )
    def get(self, request, uuid):
        metadata_only = request.GET.get("metadata") is not None
        from django.core.exceptions import PermissionDenied
        from django.http import Http404
        try:
            response_data = MediaService.get_encrypted_media_response(uuid, request.user, metadata_only=metadata_only)
            if metadata_only:
                return JsonResponse(response_data)
            return response_data
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=403)
        except Http404 as e:
            return Response({"detail": str(e)}, status=404)


class MediaUploadView(APIView):
    """Upload encrypted media files with recipient access control."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [MediaUploadRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload encrypted media file",
        description="Upload binary file payload with JSON metadata listing allowed recipient usernames.",
        request=MediaUploadSerializer,
        responses={200: MediaUploadResponseSerializer, 400: SimpleSuccessResponseSerializer}
    )
    def post(self, request):
        file_data = request.FILES.get('file')
        json_metadata = request.data.get('metadata')

        if not (file_data and json_metadata):
            return Response({"detail": "No file data or metadata specified"}, status=400)

        try:
            media = MediaService.save_encrypted_media(file_data, json_metadata, request.user)
            return Response({"src": str(media.uuid)}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class UserPublicKeyView(APIView):
    """Fetch or set user E2EE public keys."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [PublicKeyRateThrottle]

    @extend_schema(
        summary="Fetch public keys by list of usernames",
        description="Retrieve public keys for given array of usernames in query string.",
        parameters=[
            OpenApiParameter("username", OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Username to fetch key for (can be passed multiple times)", many=True)
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        user_list = request.GET.getlist('username', [])
        hash_bucket = {}

        for username in user_list:
            try:
                user = User.objects.get(username=username)
                user_id = str(user.id)
            except User.DoesNotExist:
                pass
            else:
                hash_bucket[user_id] = user.public_key if user.public_key else None

        return Response(hash_bucket)

    @extend_schema(
        summary="Update current user's E2EE public key",
        description="Set or replace current user's public key string.",
        request=UserPublicKeySetSerializer,
        responses={200: SimpleSuccessResponseSerializer}
    )
    def post(self, request):
        serializer = UserPublicKeySetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        public_key = serializer.validated_data.get("publicKey")
        
        request.user.public_key = public_key
        request.user.save()
        return Response({"success": "Public_key successfully set"})


class UserProfileEdit(APIView):
    """Edit display picture or bio."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Update user profile (DP / Bio)",
        description="Upload a new profile image (jpg, jpeg, png) or set bio string.",
        request=UserProfileEditSerializer,
        responses={200: UserProfileEditResponseSerializer, 400: SimpleSuccessResponseSerializer}
    )
    def post(self, request):
        file_data = request.FILES.get('dp')
        new_bio = request.data.get('bio')
        
        if file_data:
            try:
                filename = MediaService.save_profile_picture(file_data)
                request.user.dp = filename
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if new_bio:
            request.user.bio = new_bio

        request.user.save()
        dp_url = MediaService.build_profile_picture_url(request.user.dp, request)
        return Response({"success": "Profile has been updated", "new_dp": dp_url}, status=200)


class UserView(APIView):
    """Fetch user profile details."""
    permission_classes = [AllowAny]
    authentication_classes = [CookieJWTAuthentication]

    @extend_schema(
        summary="Get user profile details",
        description="Retrieve profile details for given username or 'me' for currently logged in user.",
        responses={200: UserSerializer}
    )
    def get(self, request, username):
        query = username if username != "me" else (request.user.username if request.user.is_authenticated else "")
        user = get_object_or_404(User, username=query)

        if request.user.is_authenticated:
            serializer = UserSerializer(user)
            return Response(serializer.data)
        
        serializer = PublicUserSerializer(user)
        return Response(serializer.data)


class UserSettingsView(APIView):
    """Get or update user settings / preferences."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get user settings JSON",
        description="Retrieve user profile_data JSON object containing preferences.",
        responses={200: UserSettingsSerializer}
    )
    def get(self, request):
        return Response({"profile_data": request.user.profile_data})

    @extend_schema(
        summary="Update user settings JSON",
        description="Update key-value pairs in user profile_data preferences.",
        request=UserSettingsSerializer,
        responses={200: UserSettingsSerializer}
    )
    def post(self, request):
        serializer = UserSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_data = serializer.validated_data.get('profile_data', {})
        request.user.profile_data.update(updated_data)
        request.user.save()
        return Response({"profile_data": request.user.profile_data})


class UserSearchView(APIView):
    """Search registered users by username."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Search users by username query",
        description="Returns list of users matching query string for contact discovery. Public fields only if unauthenticated.",
        parameters=[
            OpenApiParameter("q", OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Search term for username", required=True)
        ],
        responses={200: UserSerializer(many=True)}
    )
    def get(self, request):
        query = request.GET.get("q", "").strip()
        if not query:
            return Response([])
            
        users = User.objects.filter(username__icontains=query)
        if request.user.is_authenticated:
            users = users.exclude(id=request.user.id)
            serializer = UserSerializer(users[:20], many=True)
        else:
            serializer = PublicUserSerializer(users[:20], many=True)
            
        return Response(serializer.data)


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Register a new user account",
        description="Creates a new account with username, email, and password.",
        responses={201: UserSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@csrf_exempt
def index(request, methods=['GET', 'POST']):
    cookies = request.COOKIES
    return JsonResponse(cookies)


def random_name(length=10):
    choices = [ random.choice(ascii_lowercase) for _ in range(length) ]
    return ''.join(choices)


def save_to_file(root, data, ext):
    file_path = root / f"{random_name()}.{ext}"

    while os.path.exists(file_path):
        file_path = root / f"{random_name()}.{ext}"

    with open(file_path, 'wb') as destination:
        for chunk in data.chunks():
            destination.write(chunk)
    
    return file_path
