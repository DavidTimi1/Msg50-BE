
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from chat.token_auth import CookieGuestLoginView, CookieTokenObtainPairView, CookieTokenRefreshView, CookieTokenVerifyView
from chat.views import RegisterView
from .view import health_check, ServeMediaFileView, run_stale_users_cleanup
from django.conf.urls.static import static


api_v2_patterns = [
    path('', include("chat.urls")),
    path('healthz', health_check, name='health_check'),
    path('cleanup/stale-users', run_stale_users_cleanup, name='cleanup_stale_users'),

    path('feedback/', include("feedback.urls")),

    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/login', CookieTokenObtainPairView.as_view(), name='login'),
    path('auth/refresh', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify', CookieTokenVerifyView.as_view(), name='token_verify'),
    path('auth/guest', CookieGuestLoginView.as_view(), name='guest_login'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v2/', include(api_v2_patterns)),
    path('media/<str:file_name>', ServeMediaFileView.as_view(), name='media_file'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)