"""
API Views DRF para o app assistant — endpoints REST com autenticação JWT.
"""
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser

from .serializers import (
    TextInputSerializer,
    AudioInputSerializer,
    ConfirmSerializer,
    AssistantInteractionSerializer,
    TransactionPreviewSerializer,
)
from .services import (
    transcribe_audio,
    interpret_transaction,
    create_interaction,
    confirm_interaction,
    cancel_interaction,
    ServiceError,
)
from .selectors import get_user_interactions, get_interaction_by_id


class AssistantTextAPIView(APIView):
    """
    POST /api/v1/assistant/text/

    Recebe texto em linguagem natural, interpreta via LLM e retorna preview
    da transação extraída ou uma pergunta de clarificação se houver campos faltantes.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Interpreta texto, cria interação e retorna preview ou pergunta de clarificação."""
        serializer = TextInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message = serializer.validated_data["message"]

        try:
            llm_response = interpret_transaction(request.user, message)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        # Verificar se há campos obrigatórios faltando (excetuando description e card)
        campos_obrigatorios = {"name", "amount", "type", "category", "date"}
        faltando = set(llm_response.get("missing_fields", [])) & campos_obrigatorios

        if faltando:
            interaction = create_interaction(
                user=request.user,
                input_type="texto",
                input_content=message,
                llm_response=llm_response,
            )
            return Response(
                {
                    "question": "Por favor, forneça os seguintes campos: " + ", ".join(sorted(faltando)),
                    "interaction_id": str(interaction.id),
                    "missing_fields": list(faltando),
                },
                status=status.HTTP_200_OK,
            )

        interaction = create_interaction(
            user=request.user,
            input_type="texto",
            input_content=message,
            llm_response=llm_response,
        )

        preview_serializer = TransactionPreviewSerializer(data=llm_response)
        preview_serializer.is_valid()

        return Response(
            {
                "interaction_id": str(interaction.id),
                "preview": llm_response,
            },
            status=status.HTTP_200_OK,
        )


class AssistantAudioAPIView(APIView):
    """
    POST /api/v1/assistant/audio/

    Recebe arquivo de áudio, transcreve via Whisper, interpreta via LLM e retorna
    preview da transação extraída ou uma pergunta de clarificação.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        """Transcreve áudio, interpreta texto resultante, cria interação e retorna preview."""
        serializer = AudioInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        audio_file = serializer.validated_data["audio"]

        try:
            transcribed_text = transcribe_audio(audio_file)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        try:
            llm_response = interpret_transaction(request.user, transcribed_text)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        # Verificar se há campos obrigatórios faltando
        campos_obrigatorios = {"name", "amount", "type", "category", "date"}
        faltando = set(llm_response.get("missing_fields", [])) & campos_obrigatorios

        if faltando:
            interaction = create_interaction(
                user=request.user,
                input_type="audio",
                input_content=transcribed_text,
                llm_response=llm_response,
            )
            return Response(
                {
                    "question": "Por favor, forneça os seguintes campos: " + ", ".join(sorted(faltando)),
                    "interaction_id": str(interaction.id),
                    "missing_fields": list(faltando),
                    "transcription": transcribed_text,
                },
                status=status.HTTP_200_OK,
            )

        interaction = create_interaction(
            user=request.user,
            input_type="audio",
            input_content=transcribed_text,
            llm_response=llm_response,
        )

        return Response(
            {
                "interaction_id": str(interaction.id),
                "transcription": transcribed_text,
                "preview": llm_response,
            },
            status=status.HTTP_200_OK,
        )


class AssistantConfirmAPIView(APIView):
    """
    POST /api/v1/assistant/confirm/<uuid:pk>/

    Confirma uma interação pendente, criando a transação financeira correspondente.
    Aceita ajustes opcionais nos dados extraídos via adjusted_data.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Confirma interação e cria transação; retorna status e transaction_id."""
        serializer = ConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        adjusted_data = serializer.validated_data.get("adjusted_data")

        try:
            transaction = confirm_interaction(
                interaction_id=pk,
                user=request.user,
                adjusted_data=adjusted_data,
            )
        except ServiceError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "status": "confirmed",
                "transaction_id": str(transaction.id),
            },
            status=status.HTTP_200_OK,
        )


class AssistantCancelAPIView(APIView):
    """
    POST /api/v1/assistant/cancel/<uuid:pk>/

    Cancela uma interação pendente do assistente.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Cancela interação e retorna status cancelado."""
        try:
            cancel_interaction(interaction_id=pk, user=request.user)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "cancelled"}, status=status.HTTP_200_OK)


class AssistantHistoryAPIView(ListAPIView):
    """
    GET /api/v1/assistant/history/

    Retorna o histórico de interações do assistente para o usuário autenticado.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AssistantInteractionSerializer

    def get_queryset(self):
        """Retorna interações do usuário autenticado, ordenadas por data de criação decrescente."""
        return get_user_interactions(self.request.user).order_by("-created_at")
