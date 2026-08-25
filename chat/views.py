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
from e2ee_chatapp.settings import ENCRYPTED_MEDIA_ROOT, MEDIA_ROOT

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
        media = get_object_or_404(Media, uuid=uuid)

        # Check if the user has access to the media file
        if request.user.id not in media.access_ids.values_list('id', flat=True):
            return Response({"detail": "You do not have permission to access this file."}, status=403)
        
        if request.GET.get("metadata") is not None:
            # send metadata without recipients property
            return JsonResponse({k: v for k, v in media.metadata.items() if k != "recipients"})

        # Serve the file
        response = FileResponse(open(media.filePath, "rb"), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{media.metadata.get("name", "media")}.bin"'
        return response        


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
        
        file_path = save_to_file(ENCRYPTED_MEDIA_ROOT, file_data, 'bin')
        try:
            metadata = json.loads(json_metadata) if isinstance(json_metadata, str) else json_metadata
        except Exception:
            metadata = {}

        allowed = [request.user.id]

        recipients = metadata.get("recipients", [])
        for recipient in recipients:
            try:
                allowed.append(User.objects.get(username=recipient))
            except User.DoesNotExist:
                continue

        media = Media.objects.create(metadata=metadata, filePath=file_path)
        media.access_ids.set(allowed)
        return Response({"src": str(media.uuid)}, status=200)


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
        file_path = None
        
        if file_data:
            ext = file_data.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png']:
                return Response({"detail": "Invalid file type. Only jpg, jpeg, png allowed."}, status=400)

            file_path = str(save_to_file(MEDIA_ROOT, file_data, ext))
            request.user.dp = file_path

        if new_bio:
            request.user.bio = new_bio

        request.user.save()
        return Response({"success": "Profile has been updated", "new_dp": file_path}, status=200)


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
            
        users = User.objects.filter(username__icontains=query)[:20]
        if request.user.is_authenticated:
            users = users.exclude(id=request.user.id)
            serializer = UserSerializer(users, many=True)
        else:
            serializer = PublicUserSerializer(users, many=True)
            
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
