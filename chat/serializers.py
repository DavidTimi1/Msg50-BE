from .models import Message, Media
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, CharField, ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model

from chat.services.media_service import MediaService

User = get_user_model()


class UserSerializer(ModelSerializer):
    dp = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', "username", "email", "public_key", "bio", "profile_data", "dp"]

    def get_dp(self, obj):
        request = self.context.get('request')
        return MediaService.build_profile_picture_url(obj.dp, request)


class PublicUserSerializer(ModelSerializer):
    dp = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', "username", "public_key", "bio", "dp"]

    def get_dp(self, obj):
        request = self.context.get('request')
        return MediaService.build_profile_picture_url(obj.dp, request)


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
        fields = ('username', 'email', 'password')

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


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Registered username")
    password = serializers.CharField(write_only=True, help_text="User password")


class AuthSuccessSerializer(serializers.Serializer):
    message = serializers.CharField()
    user_id = serializers.UUIDField()
    username = serializers.CharField()


class UserPublicKeySetSerializer(serializers.Serializer):
    publicKey = serializers.CharField(help_text="PEM or Base64 encoded public key string")


class UserProfileEditSerializer(serializers.Serializer):
    dp = serializers.ImageField(required=False, help_text="User profile picture file (jpg, jpeg, png)")
    bio = serializers.CharField(required=False, max_length=500, help_text="User bio/status string")


class UserProfileEditResponseSerializer(serializers.Serializer):
    success = serializers.CharField()
    new_dp = serializers.CharField(allow_null=True)


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Encrypted media binary payload")
    metadata = serializers.CharField(help_text="JSON string with recipients array and metadata")


class MediaUploadResponseSerializer(serializers.Serializer):
    src = serializers.UUIDField(help_text="Access UUID for uploaded media")


class UserSettingsSerializer(serializers.Serializer):
    profile_data = serializers.JSONField(help_text="User preference settings key-value JSON")


class SimpleSuccessResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()