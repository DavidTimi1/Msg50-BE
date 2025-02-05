
# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from django.shortcuts import get_object_or_404, render
from django.core.files.storage import default_storage
from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import UserSerializer, MessageSerializer, MediaSerializer, RegisterSerializer
from .models import Message, Media


from django.contrib.auth import get_user_model

User = get_user_model()


class MessageViewSet(viewsets.ModelViewSet):
    """CRUD operations for messages."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Show only messages sent to the logged-in user
        return self.queryset.filter(recipient=self.request.user)

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


class MediaUploadView(APIView):
    """Upload encrypted media files."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Handle file uploads
        file = request.FILES['file']
        metadata = request.data.get('metadata', {})
        media = Media.objects.create(metadata=metadata)
        media.file.save(file.name, file)
        media.access_ids.set([request.user.id] + metadata.get("recipients", []))
        return Response({"uuid": media.uuid})


class UserPublicKeyView(APIView):
    """Fetch the public key of a user based on their username."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        user = User.objects.get(username=username)
        return Response({"public_key": user.public_key})


class UserView(APIView):
    """Fetch the data of a user based on their username."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, username):
        query = username if username != "me" else request.user.username
        user = User.objects.get(username=query)
        serializer = self.serializer_class(user)
        return Response(serializer.data)



# Registration View
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

@csrf_exempt
def index(request, methods=['GET', 'POST']):
    # send the cookies sent by frontend as json
    cookies = request.COOKIES
    return JsonResponse(cookies)