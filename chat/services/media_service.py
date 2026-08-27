import os
import uuid
import json
from django.conf import settings
from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from chat.models import Media

User = get_user_model()

class MediaService:
    @staticmethod
    def save_profile_picture(file_data) -> str:
        """
        Validates and saves a public profile picture.
        Returns the saved filename (relative path).
        """
        ext = file_data.name.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png']:
            raise ValueError("Invalid file type. Only jpg, jpeg, png allowed.")
        
        # Ensure the directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        
        with open(file_path, 'wb') as destination:
            for chunk in file_data.chunks():
                destination.write(chunk)
                
        return filename

    @staticmethod
    def build_profile_picture_url(dp_value, request=None) -> str:
        """
        Generates the absolute/relative URL for a profile picture.
        """
        if not dp_value:
            return None
        
        # Parse out filename from legacy absolute paths if present
        if 'media/uploads/' in dp_value:
            filename = dp_value.split('media/uploads/')[-1]
        elif '/' in dp_value or '\\' in dp_value:
            filename = os.path.basename(dp_value)
        else:
            filename = dp_value
            
        relative_url = f"{settings.MEDIA_URL}{filename}"
        
        if request:
            return request.build_absolute_uri(relative_url)
            
        # Fallback if no request context
        scheme = "https" if not settings.DEBUG else "http"
        host = settings.HOST_NAME
        # If host name does not contain port in local dev, add standard port 8000
        if settings.DEBUG and ":" not in host:
            host = f"{host}:8000"
        return f"{scheme}://{host}{relative_url}"

    @staticmethod
    def save_encrypted_media(file_data, json_metadata, uploader) -> Media:
        """
        Saves an encrypted media blob with access control for recipients.
        """
        # Ensure the directory exists
        os.makedirs(settings.ENCRYPTED_MEDIA_ROOT, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex}.bin"
        file_path = os.path.join(settings.ENCRYPTED_MEDIA_ROOT, filename)
        
        with open(file_path, 'wb') as destination:
            for chunk in file_data.chunks():
                destination.write(chunk)
                
        try:
            metadata = json.loads(json_metadata) if isinstance(json_metadata, str) else json_metadata
        except Exception:
            metadata = {}
            
        allowed = [uploader.id]
        recipients = metadata.get("recipients", [])
        for recipient in recipients:
            try:
                allowed.append(User.objects.get(username=recipient))
            except User.DoesNotExist:
                continue
                
        # Store only the filename in the filePath field for portability
        media = Media.objects.create(metadata=metadata, filePath=filename)
        media.access_ids.set(allowed)
        return media

    @staticmethod
    def get_encrypted_media_response(media_uuid, user, metadata_only=False):
        """
        Fetches an encrypted media blob and checks authorization.
        Returns JSON metadata dict or a FileResponse object.
        """
        try:
            media = Media.objects.get(uuid=media_uuid)
        except Media.DoesNotExist:
            raise Http404("Media file not found")
            
        # Check authorization
        if user.id not in media.access_ids.values_list('id', flat=True):
            raise PermissionDenied("You do not have permission to access this file.")
            
        if metadata_only:
            # Exclude recipients list from public metadata response
            return {k: v for k, v in media.metadata.items() if k != "recipients"}
            
        # Support legacy absolute path in database or new relative filename
        if os.path.isabs(media.filePath):
            file_path = media.filePath
        else:
            file_path = os.path.join(settings.ENCRYPTED_MEDIA_ROOT, media.filePath)
            
        if not os.path.exists(file_path):
            raise Http404("File not found on disk")
            
        response = FileResponse(open(file_path, "rb"), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{media.metadata.get("name", "media")}.bin"'
        return response
