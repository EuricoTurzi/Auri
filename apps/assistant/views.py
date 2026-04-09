"""
Views SSR do módulo assistant.

Responsabilidades:
- Renderizar a página principal do assistente
- Processar entrada de texto e áudio via AJAX (retornam JsonResponse)
- Confirmar ou cancelar interações pendentes
"""

import json

from django.apps import apps
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


def _build_llm_response(interaction, llm_data):
    """
    Monta o JsonResponse adequado com base nos dados retornados pela LLM.

    Prioridade:
    1. missing_fields → status "missing" (solicitar campos obrigatórios ausentes)
    2. suggested_category_name sem category → status "suggest_category"
    3. caso contrário → status "preview"
    """
    missing_fields = llm_data.get("missing_fields", [])
    suggested_category_name = llm_data.get("suggested_category_name")
    assistant_message = llm_data.get("assistant_message", "")

    if missing_fields:
        question = assistant_message or "Preciso de mais alguns dados para registrar a transação."
        return JsonResponse({
            "status": "missing",
            "interaction_id": str(interaction.id),
            "missing_fields": missing_fields,
            "question": question,
        })

    if suggested_category_name and not llm_data.get("category"):
        return JsonResponse({
            "status": "suggest_category",
            "interaction_id": str(interaction.id),
            "suggested_category_name": suggested_category_name,
            "data": llm_data,
            "assistant_message": assistant_message or f"Não encontrei a categoria '{suggested_category_name}' no sistema. Deseja criá-la?",
        })

    return JsonResponse({
        "status": "preview",
        "interaction_id": str(interaction.id),
        "data": llm_data,
        "assistant_message": assistant_message,
    })


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

        return _build_llm_response(interaction, llm_data)


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

        return _build_llm_response(interaction, llm_data)


class AssistantConfirmView(LoginRequiredMixin, View):
    """POST /assistant/confirm/<uuid:pk>/ — confirma uma interação pendente."""

    def post(self, request, pk):
        adjusted_data = None

        if request.body:
            try:
                body = json.loads(request.body)
                # Aceita tanto {adjusted_data: {...}} quanto o objeto diretamente
                adjusted_data = body.get("adjusted_data") or (body if body else None)
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


class AssistantCreateCategoryView(LoginRequiredMixin, View):
    """POST /assistant/create-category/ — cria a categoria sugerida e retorna o preview."""

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({"error": "Corpo da requisição inválido."}, status=400)

        interaction_id = body.get("interaction_id", "").strip()
        category_name = body.get("category_name", "").strip()

        if not interaction_id or not category_name:
            return JsonResponse(
                {"error": "interaction_id e category_name são obrigatórios."},
                status=400,
            )

        Category = apps.get_model("categories", "Category")
        category, _ = Category.objects.get_or_create(
            user=request.user,
            name=category_name,
            defaults={"is_active": True},
        )

        AssistantInteraction = apps.get_model("assistant", "AssistantInteraction")
        try:
            interaction = AssistantInteraction.objects.get(
                id=interaction_id, user=request.user
            )
        except AssistantInteraction.DoesNotExist:
            return JsonResponse({"error": "Interação não encontrada."}, status=404)

        llm_data = dict(interaction.llm_response)
        llm_data["category"] = {"id": str(category.id), "name": category.name}
        llm_data["suggested_category_name"] = None
        interaction.llm_response = llm_data
        interaction.save()

        return JsonResponse({
            "status": "preview",
            "interaction_id": str(interaction.id),
            "data": llm_data,
            "assistant_message": f"Categoria '{category_name}' criada! Confira os dados abaixo.",
        })
