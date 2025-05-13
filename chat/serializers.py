from .models import Message, Media
from rest_framework.serializers import ModelSerializer, CharField, ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', "username", "email", "public_key", "bio", "profile_data", "dp"]


class MessageSerializer(ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "receiver", "encrypted_message"]


class MediaSerializer(ModelSerializer):
    class Meta:
        model = Media
        fields = ["uuid", "file", "metadata", "access_ids"]


class RegisterSerializer(ModelSerializer):
    password = CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')  # Add other fields if needed

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        return user




class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['uuid'] = str(user.id)
        return token