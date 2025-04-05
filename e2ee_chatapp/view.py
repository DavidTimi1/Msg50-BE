
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings
from rest_framework.views import APIView
import os


def health_check(request):
    return JsonResponse({"success": "true"})


class ServeMediaFileView(APIView):
    """Serve files from the media/uploads folder."""

    def get(self, request, file_name):
        # Construct the full file path
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)

        # Check if the file exists
        if not os.path.exists(file_path):
            raise Http404("File not found")
        
        return FileResponse(open(file_path, 'rb'), content_type='application/octet-stream')