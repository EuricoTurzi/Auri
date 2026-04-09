"""
URLs do módulo assistant.
"""

from django.urls import path

from apps.assistant.views import (
    AssistantAudioView,
    AssistantCancelView,
    AssistantConfirmView,
    AssistantTextView,
    AssistantView,
)

app_name = "assistant"

urlpatterns = [
    path("assistant/", AssistantView.as_view(), name="assistant"),
    path("assistant/text/", AssistantTextView.as_view(), name="text"),
    path("assistant/audio/", AssistantAudioView.as_view(), name="audio"),
    path("assistant/confirm/<uuid:pk>/", AssistantConfirmView.as_view(), name="confirm"),
    path("assistant/cancel/<uuid:pk>/", AssistantCancelView.as_view(), name="cancel"),
]
