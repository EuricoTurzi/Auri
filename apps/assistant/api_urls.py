"""
URLs da API REST para o app assistant.
"""
from django.urls import path

from apps.assistant import api_views

app_name = "assistant_api"

urlpatterns = [
    path("text/", api_views.AssistantTextAPIView.as_view(), name="text"),
    path("audio/", api_views.AssistantAudioAPIView.as_view(), name="audio"),
    path("confirm/<uuid:pk>/", api_views.AssistantConfirmAPIView.as_view(), name="confirm"),
    path("cancel/<uuid:pk>/", api_views.AssistantCancelAPIView.as_view(), name="cancel"),
    path("history/", api_views.AssistantHistoryAPIView.as_view(), name="history"),
]
