from django.http import JsonResponse
from .models import Feedback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import FeedbackSerializer
from django.core.mail import send_mail
from django.conf import settings


class FeedbackView(APIView):
    def post(self, request, project_name):
        # insert project name based on subroute
        serializer = FeedbackSerializer(data=request.data.dict() | {"project_name": project_name.lower() })


        if serializer.is_valid():
            serializer.save()

            return JsonResponse({"success": "Feedback submitted successfully"}, status=status.HTTP_201_CREATED)

        return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


    def get(self, request, project_name=None):
        if not request.user.is_superuser:
            return Response({"success": False, "error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        if project_name:
            feedbacks = Feedback.objects.filter(project_name=project_name)
        else:
            feedbacks = Feedback.objects.all()

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date and end_date:
            feedbacks = feedbacks.filter(created_at__range=[start_date, end_date])

        serializer = FeedbackSerializer(feedbacks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


class FeedbackReplyView(APIView):
    def post(self, request, feedback_id):

        feedback = Feedback.objects.filter(id=feedback_id).first()
        if not feedback:
            return Response({"success": False, "error": "Feedback not found"}, status=status.HTTP_404_NOT_FOUND)

        reply_message = request.data.get('message')
        if not reply_message:
            return Response({"success": False, "error": "Reply message is required"}, status=status.HTTP_400_BAD_REQUEST)

        user_email = feedback.user_email  # Assuming Feedback model has a `user_email` field
        send_mail(
            subject="Reply to your feedback",
            message=reply_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
        )

        return Response({"success": True, "message": "Reply sent successfully"}, status=status.HTTP_200_OK)