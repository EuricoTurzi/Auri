"""
API Views DRF para o app cards — endpoints REST com autenticação JWT.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import CardSerializer, CardCreateUpdateSerializer
from .services import create_card, update_card, deactivate_card
from .selectors import get_user_cards, get_card_by_id, get_card_transactions
from apps.transactions.serializers import TransactionSerializer


class CardListCreateAPIView(APIView):
    """
    GET  /api/v1/cards/  — lista cartões ativos do usuário autenticado.
    POST /api/v1/cards/  — cria um novo cartão; retorna 201.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Cards'],
        summary='Listar cartões',
        responses={200: CardSerializer(many=True)},
    )
    def get(self, request):
        """Retorna lista de cartões ativos com available_limit calculado."""
        cards = get_user_cards(request.user)
        serializer = CardSerializer(cards, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Cards'],
        summary='Criar cartão',
        request=CardCreateUpdateSerializer,
        responses={201: CardSerializer},
    )
    def post(self, request):
        """Cria cartão com dados validados e retorna 201 com representação completa."""
        serializer = CardCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            card = create_card(user=request.user, **serializer.validated_data)
            return Response(CardSerializer(card).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)


class CardDetailAPIView(APIView):
    """
    GET    /api/v1/cards/<uuid:pk>/  — detalhe do cartão com available_limit.
    PUT    /api/v1/cards/<uuid:pk>/  — atualiza dados do cartão.
    DELETE /api/v1/cards/<uuid:pk>/  — soft-delete; retorna 204.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Cards'],
        summary='Detalhe do cartão',
        responses={200: CardSerializer},
    )
    def get(self, request, pk):
        """Retorna dados completos de um cartão específico do usuário."""
        try:
            card = get_card_by_id(pk, request.user)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(CardSerializer(card).data)

    @extend_schema(
        tags=['Cards'],
        summary='Atualizar cartão',
        request=CardCreateUpdateSerializer,
        responses={200: CardSerializer},
    )
    def put(self, request, pk):
        """Atualiza campos do cartão e retorna representação atualizada."""
        serializer = CardCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            card = update_card(pk, request.user, **serializer.validated_data)
            return Response(CardSerializer(card).data)
        except (ValidationError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Cards'],
        summary='Remover cartão (soft-delete)',
        responses={204: None},
    )
    def delete(self, request, pk):
        """Realiza soft-delete do cartão; retorna 204 sem corpo."""
        try:
            deactivate_card(pk, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)


class CardTransactionsAPIView(APIView):
    """
    GET /api/v1/cards/<uuid:pk>/transactions/  — lista transações do cartão.

    Query params opcionais:
        billing_period: não utilizado diretamente aqui — o selector aceita tupla
                        (date_start, date_end); extensão futura via query params.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Cards'],
        summary='Listar transações do cartão',
        parameters=[
            OpenApiParameter(
                name='billing_period',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Período de faturamento no formato YYYY-MM-DD,YYYY-MM-DD',
                required=False,
            ),
        ],
        responses={200: TransactionSerializer(many=True)},
    )
    def get(self, request, pk):
        """
        Retorna transações vinculadas ao cartão.
        Aceita query param `billing_period` (formato 'YYYY-MM-DD,YYYY-MM-DD') opcional.
        """
        billing_period = None
        raw_period = request.query_params.get("billing_period")
        if raw_period:
            try:
                from datetime import date
                partes = raw_period.split(",")
                if len(partes) != 2:
                    raise ValueError("Formato inválido.")
                date_start = date.fromisoformat(partes[0].strip())
                date_end = date.fromisoformat(partes[1].strip())
                billing_period = (date_start, date_end)
            except (ValueError, AttributeError):
                return Response(
                    {"detail": "Parâmetro billing_period inválido. Use o formato 'YYYY-MM-DD,YYYY-MM-DD'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            transactions = get_card_transactions(pk, request.user, billing_period=billing_period)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        # Quando o app transactions tiver seu próprio serializer, importá-lo aqui.
        # Por ora, serializa apenas os campos básicos disponíveis no model.
        try:
            from apps.transactions.serializers import TransactionSerializer
            data = TransactionSerializer(transactions, many=True).data
        except (ImportError, Exception):
            # Fallback: retorna lista vazia se o serializer ainda não existir
            data = list(transactions.values()) if hasattr(transactions, "values") else []

        return Response(data)
