from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MediaAccessView, MessageViewSet, MediaUploadView, UserProfileEdit, UserPublicKeyView, index, UserView

# Create a router for the ViewSet
router = DefaultRouter()
router.register(r'messages', MessageViewSet, basename='message')

# Define the urlpatterns for the app
urlpatterns = [
    path('', index, name='index'),  # Index view    
    path('api/', include(router.urls)),  # MessageViewSet endpoints (CRUD operations)
    
    path('api/media/<str:uuid>', MediaAccessView.as_view(), name='media-access'),  # Media upload endpoint
    path('api/media/upload/', MediaUploadView.as_view(), name='media-upload'),  # Media upload endpoint
    path('api/user/<str:username>', UserView.as_view(), name='user-details'),  # User details endpoint
    path('api/user/public-key/', UserPublicKeyView.as_view(), name='user-public-key'),  # Public key fetch
    path('api/profile-edit', UserProfileEdit.as_view(), name='profile-edit'),  # Profile edit endpoint
]
