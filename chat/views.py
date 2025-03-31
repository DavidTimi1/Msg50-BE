import json
import os
import random
import re
from string import ascii_lowercase
import uuid

# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, JsonResponse

from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from e2ee_chatapp.settings import MEDIA_ROOT

from .serializers import UserSerializer, MessageSerializer, RegisterSerializer
from .models import Message, Media


from django.contrib.auth import get_user_model

User = get_user_model()


class MessageViewSet(viewsets.ModelViewSet):
    """CRUD operations for messages."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Show only messages sent to the logged-in user
        return self.queryset.filter(receiver_id=self.request.user)

    def post(self, request):
        data = request.data
        iv = data.get('iv')
        encrypted_key = data.get('key')
        file_id = data.get('file')
        encrypted_data = data.get('data')
        
        # Generate UUID on the backend
        uuid_value = uuid.uuid4()

        # Create and save the message
        message = Message.objects.create(
            uuid=uuid_value,
            iv=iv,
            encrypted_key=encrypted_key,
            file_id=file_id,
            encrypted_data=encrypted_data,
            sender=request.user
        )

        # Serialize the message
        serializer = MessageSerializer(message)

        return Response(serializer.data, status=201)


class MediaAccessView(APIView):
    """Access uploaded media files."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        media = get_object_or_404(Media, uuid=uuid)

        # Check if the user has access to the media file
        if request.user.id not in media.access_ids.values_list('id', flat=True):
            return Response({"error": "You do not have permission to access this file."}, status=403)
        
        if request.GET.get("metadata") is not None:
            # send metadata without recipients property
            return JsonResponse({k: v for k, v in media.metadata.items() if k != "recipients"})

        # Serve the file
        response = FileResponse(open(media.filePath, "rb"), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{media.metadata.get("name")}.bin"'
        return response        


class MediaUploadView(APIView):
    """Upload encrypted media files."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]    

    def post(self, request):

        file_data = request.FILES.get('file')
        json_metadata = request.data.get('metadata')
        # Handle file uploads
        if not (file_data and json_metadata):
            return Response("No file data specified", 404)
        
        file_path = save_to_file(file_data)
        metadata = json.loads(json_metadata)
        allowed = [request.user.id]

        for recipient in metadata["recipients"]:
            try:
                allowed.append(User.objects.get(username=recipient))
            except:
                continue

        media = Media.objects.create(metadata=metadata, filePath=file_path)

        media.access_ids.set(allowed)
        return Response({"src": media.uuid})


class UserPublicKeyView(APIView):
    """Fetch the public key of a user based on their username."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # get all request queries id as a list
        user_list = request.GET.getlist('username', [])
        hash_bucket = {}

        for username in user_list:
            try:
                user = User.objects.get(username=username)
                user_id = str(user.id)

            except:
                # user existeth not
                pass
            else:
                hash_bucket[user_id] = user.public_key if user.public_key else None

        return Response(hash_bucket)
    

    def post(self, request):
        public_key = request.data.get("publicKey")
        
        if public_key:
            # if request.user.public_key:
                # return Response({"Error": "Would require 2fa for this action to be completed"}, status=400)
            
            request.user.public_key = public_key
            request.user.save()
            return Response({"success": "Public_key successfully set"})





class UserView(APIView):
    """Fetch the data of a user based on their username."""
    serializer_class = UserSerializer

    def get(self, request, username):
        query = username if username != "me" else request.user.username
        user = get_object_or_404(User, username=query)
        
        serializer = self.serializer_class(user)

        # if user is authenticated show all the data
        if request.user.is_authenticated:
            return Response(serializer.data)
        
        # if user is not authenticated show only public data in html
        return render(request, "chat/profile.html", {"user": serializer.data})



# Registration View
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

@csrf_exempt
def index(request, methods=['GET', 'POST']):
    # send the cookies sent by frontend as json
    cookies = request.COOKIES
    return JsonResponse(cookies)


def random_name(length=10):
    choices = [ random.choice(ascii_lowercase) for _ in range(length) ]
    return ''.join(choices)


def save_to_file(data):
    file_path = MEDIA_ROOT / f"{random_name()}.bin"

    while os.path.exists(file_path):
        file_path = MEDIA_ROOT / f"{random_name()}.bin"

    with open(file_path, 'wb') as destination:
        for chunk in data.chunks():
            destination.write(chunk)
    
    return file_path
