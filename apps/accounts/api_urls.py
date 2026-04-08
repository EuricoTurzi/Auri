from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts import api_views

urlpatterns = [
    path('register/', api_views.RegisterAPIView.as_view(), name='api_register'),
    path('login/', api_views.LoginAPIView.as_view(), name='api_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('change-password/', api_views.ChangePasswordAPIView.as_view(), name='api_change_password'),
    path('me/', api_views.MeAPIView.as_view(), name='api_me'),
]
