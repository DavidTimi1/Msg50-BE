import os
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings
from django.core.management import call_command
from django.views.decorators.http import require_GET

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiTypes
from chat.serializers import SimpleSuccessResponseSerializer


def health_check(request):
    """Health check endpoint for deployment monitoring."""
    return JsonResponse({"status": "healthy", "success": "true"})


@require_GET
def run_stale_users_cleanup(request):
    """System task endpoint to delete aged guest accounts."""
    try:
        call_command('delete_aged_guests')
        return JsonResponse({"status": "Cleanup of stale users completed successfully"})
    except Exception as e:
        return JsonResponse({"status": "Error", "error": str(e)}, status=500)


class ServeMediaFileView(APIView):
    """Serve files directly from the media/uploads folder."""
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Serve media upload file",
        description="Stream file directly from media uploads folder by filename.",
        responses={200: OpenApiTypes.BINARY, 404: SimpleSuccessResponseSerializer}
    )
    def get(self, request, file_name):
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)

        if not os.path.exists(file_path):
            raise Http404("File not found")
        
        return FileResponse(open(file_path, 'rb'), content_type='application/octet-stream')