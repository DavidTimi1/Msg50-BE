from django.urls import path
from .views import FeedbackView

urlpatterns = [
    path('', FeedbackView.as_view(), name='all_feedbacks'),
    path('<str:project_name>', FeedbackView.as_view(), name='feedback'),
]