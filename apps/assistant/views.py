"""
Views SSR do módulo assistant.

Responsabilidades:
- Renderizar a página principal do assistente
- Processar entrada de texto e áudio via AJAX (retornam JsonResponse)
- Confirmar ou cancelar interações pendentes
"""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from apps.assistant.services import (
    ServiceError,
    cancel_interaction,
    confirm_interaction,
    create_interaction,
    interpret_transaction,
    transcribe_audio,
)


class AssistantView(LoginRequiredMixin, View):
    """GET /assistant/ — página principal do assistente."""

    template_name = "assistant/assistant.html"

    def get(self, request):
        return render(request, self.template_name)


class AssistantTextView(LoginRequiredMixin, View):
    """POST /assistant/text/ — processa entrada de texto do usuário."""

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({"error": "Corpo da requisição inválido."}, status=400)

        message = body.get("message", "").strip()
        if not message:
            return JsonResponse({"error": "O campo 'message' é obrigatório."}, status=400)

        try:
            llm_data = interpret_transaction(request.user, message)
            interaction = create_interaction(
                user=request.user,
                input_type="texto",
                input_content=message,
                llm_response=llm_data,
            )
        except ServiceError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        missing_fields = llm_data.get("missing_fields", [])

        if missing_fields:
            campos = ", ".join(missing_fields)
            question = f"Por favor informe: {campos}"
            return JsonResponse({
                "status": "missing",
                "interaction_id": str(interaction.id),
                "missing_fields": missing_fields,
                "question": question,
            })

        return JsonResponse({
            "status": "preview",
            "interaction_id": str(interaction.id),
            "data": llm_data,
        })


class AssistantAudioView(LoginRequiredMixin, View):
    """POST /assistant/audio/ — processa entrada de áudio do usuário."""

    def post(self, request):
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return JsonResponse({"error": "Nenhum arquivo de áudio enviado."}, status=400)

        try:
            transcribed_text = transcribe_audio(audio_file)
            llm_data = interpret_transaction(request.user, transcribed_text)
            interaction = create_interaction(
                user=request.user,
                input_type="audio",
                input_content=transcribed_text,
                llm_response=llm_data,
            )
        except ServiceError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        missing_fields = llm_data.get("missing_fields", [])

        if missing_fields:
            campos = ", ".join(missing_fields)
            question = f"Por favor informe: {campos}"
            return JsonResponse({
                "status": "missing",
                "interaction_id": str(interaction.id),
                "missing_fields": missing_fields,
                "question": question,
            })

        return JsonResponse({
            "status": "preview",
            "interaction_id": str(interaction.id),
            "data": llm_data,
        })


class AssistantConfirmView(LoginRequiredMixin, View):
    """POST /assistant/confirm/<uuid:pk>/ — confirma uma interação pendente."""

    def post(self, request, pk):
        adjusted_data = None

        if request.body:
            try:
                body = json.loads(request.body)
                adjusted_data = body.get("adjusted_data")
            except (json.JSONDecodeError, TypeError):
                return JsonResponse({"error": "Corpo da requisição inválido."}, status=400)

        try:
            transaction = confirm_interaction(
                interaction_id=pk,
                user=request.user,
                adjusted_data=adjusted_data,
            )
        except ServiceError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse({
            "status": "confirmed",
            "transaction_id": str(transaction.id),
        })


class AssistantCancelView(LoginRequiredMixin, View):
    """POST /assistant/cancel/<uuid:pk>/ — cancela uma interação pendente."""

    def post(self, request, pk):
        try:
            cancel_interaction(interaction_id=pk, user=request.user)
        except ServiceError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse({"status": "cancelled"})
