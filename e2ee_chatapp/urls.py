
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from chat.token_auth import CookieGuestLoginView, CookieTokenObtainPairView, CookieTokenRefreshView, CookieTokenVerifyView
from chat.views import RegisterView
from .view import health_check, ServeMediaFileView, run_stale_users_cleanup
from django.conf.urls.static import static


urlpatterns = [
    path('healthz', health_check, name='health_check'),
    path('cleanup/stale-users', run_stale_users_cleanup, name='cleanup_stale_users'),

    path('admin/', admin.site.urls),
    path('feedback/', include("feedback.urls")),
    
    path('media/<str:file_name>', ServeMediaFileView.as_view(), name='media_file'),

    path('chat/', include("chat.urls")),

    path('register', RegisterView.as_view(), name='register'),
    path('login', CookieTokenObtainPairView.as_view(), name='login'),  # For obtaining tokens
    path('token/refresh', CookieTokenRefreshView.as_view(), name='token_refresh'),  # For refreshing tokens
    path('token/verify', CookieTokenVerifyView.as_view(), name='token_verify'),  # For verifying tokens
    path('guest-login', CookieGuestLoginView.as_view(), name='guest_login'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
