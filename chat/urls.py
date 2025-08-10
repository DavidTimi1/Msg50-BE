from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MediaAccessView, MediaUploadView, UserProfileEdit, UserPublicKeyView, index, UserView

# Define the urlpatterns for the app
urlpatterns = [
    path('', index, name='index'),  # Index view
    
    path('media/<str:uuid>', MediaAccessView.as_view(), name='media-access'),  # Media upload endpoint
    path('media/upload/', MediaUploadView.as_view(), name='media-upload'),  # Media upload endpoint
    
    path('user/<str:username>', UserView.as_view(), name='user-details'),  # User details endpoint
    path('user/public-key/', UserPublicKeyView.as_view(), name='user-public-key'),  # Public key fetch
    path('user/profile-edit', UserProfileEdit.as_view(), name='profile-edit'),  # Profile edit endpoint
]
