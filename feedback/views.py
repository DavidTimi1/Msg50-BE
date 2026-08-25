from django.http import JsonResponse
from .models import Feedback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework import status
from .serializers import FeedbackSerializer
from chat.serializers import SimpleSuccessResponseSerializer
from chat.throttling import FeedbackRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.core.mail import send_mail
from django.conf import settings


class FeedbackView(APIView):
    throttle_classes = [FeedbackRateThrottle]

    @extend_schema(
        summary="Submit feedback for a project",
        description="Public endpoint to submit user feedback, bugs, or feature suggestions.",
        request=FeedbackSerializer,
        responses={201: SimpleSuccessResponseSerializer, 400: SimpleSuccessResponseSerializer}
    )
    def post(self, request, project_name="general"):
        raw_data = request.data.dict() if hasattr(request.data, 'dict') else request.data
        payload = raw_data | {"project_name": project_name.lower()}
        serializer = FeedbackSerializer(data=payload)

        if serializer.is_valid():
            serializer.save()
            return JsonResponse({"success": "Feedback submitted successfully"}, status=status.HTTP_201_CREATED)

        return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="List all feedbacks (Superuser Only)",
        description="Retrieve all submitted feedbacks filtered optionally by project_name and date range.",
        parameters=[
            OpenApiParameter("start_date", OpenApiTypes.DATE, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter("end_date", OpenApiTypes.DATE, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: FeedbackSerializer(many=True), 403: SimpleSuccessResponseSerializer}
    )
    def get(self, request, project_name=None):
        if not (request.user and request.user.is_authenticated and request.user.is_superuser):
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
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Reply to user feedback (Superuser Only)",
        description="Sends an email reply to the feedback author.",
        responses={200: SimpleSuccessResponseSerializer, 404: SimpleSuccessResponseSerializer}
    )
    def post(self, request, feedback_id):
        if not (request.user and request.user.is_authenticated and request.user.is_superuser):
            return Response({"success": False, "error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        feedback = Feedback.objects.filter(id=feedback_id).first()
        if not feedback:
            return Response({"success": False, "error": "Feedback not found"}, status=status.HTTP_404_NOT_FOUND)

        reply_message = request.data.get('message')
        if not reply_message:
            return Response({"success": False, "error": "Reply message is required"}, status=status.HTTP_400_BAD_REQUEST)

        user_email = feedback.email
        if not user_email:
            return Response({"success": False, "error": "No email provided for this feedback"}, status=status.HTTP_400_BAD_REQUEST)

        send_mail(
            subject="Reply to your feedback",
            message=reply_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@msg50.com'),
            recipient_list=[user_email],
        )

        return Response({"success": True, "message": "Reply sent successfully"}, status=status.HTTP_200_OK)