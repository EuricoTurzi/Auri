"""
API Views DRF para o app transactions — endpoints REST com autenticação JWT.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as drf_serializers, status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer

from .serializers import (
    TransactionSerializer,
    TransactionCreateSerializer,
    RecurringTransactionCreateSerializer,
    InstallmentTransactionCreateSerializer,
    InstallmentSerializer,
    TransactionFilterSerializer,
)
from .services import (
    create_transaction,
    update_transaction,
    deactivate_transaction,
    update_status,
    create_recurring_transaction,
    delete_recurring_transaction,
    create_installment_transaction,
)
from .selectors import get_user_transactions, get_transaction_by_id, get_installments


class TransactionListCreateAPIView(APIView):
    """
    GET  /api/v1/transactions/  — lista transações do usuário com filtros opcionais.
    POST /api/v1/transactions/  — cria uma nova transação; retorna 201.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Transactions'],
        summary='Listar transações',
        parameters=[
            OpenApiParameter(name='type', type=str, required=False, description='Filtro por tipo (entrada/saida)'),
            OpenApiParameter(name='category_id', type=str, required=False, description='Filtro por UUID da categoria'),
            OpenApiParameter(name='card_id', type=str, required=False, description='Filtro por UUID do cartão'),
            OpenApiParameter(name='date_start', type=str, required=False, description='Data inicial (YYYY-MM-DD)'),
            OpenApiParameter(name='date_end', type=str, required=False, description='Data final (YYYY-MM-DD)'),
            OpenApiParameter(name='status', type=str, required=False, description='Filtro por status (pendente/pago)'),
        ],
        responses={200: TransactionSerializer(many=True)},
    )
    def get(self, request):
        """Retorna lista de transações filtradas por parâmetros de query."""
        filter_serializer = TransactionFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        transactions = get_user_transactions(request.user, filters=filter_serializer.validated_data)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Transactions'],
        summary='Criar transação',
        request=TransactionCreateSerializer,
        responses={201: TransactionSerializer},
    )
    def post(self, request):
        """Cria transação simples com dados validados e retorna 201 com representação completa."""
        serializer = TransactionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            transaction = create_transaction(user=request.user, **serializer.validated_data)
            return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)


class TransactionDetailAPIView(APIView):
    """
    GET    /api/v1/transactions/<uuid:pk>/  — detalhe da transação.
    PUT    /api/v1/transactions/<uuid:pk>/  — atualiza dados da transação.
    DELETE /api/v1/transactions/<uuid:pk>/  — soft-delete; retorna 204.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Transactions'],
        summary='Detalhe da transação',
        responses={200: TransactionSerializer},
    )
    def get(self, request, pk):
        """Retorna dados completos de uma transação específica do usuário."""
        try:
            transaction = get_transaction_by_id(pk, request.user)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(TransactionSerializer(transaction).data)

    @extend_schema(
        tags=['Transactions'],
        summary='Atualizar transação',
        request=TransactionCreateSerializer,
        responses={200: TransactionSerializer},
    )
    def put(self, request, pk):
        """Atualiza campos da transação e retorna representação atualizada."""
        serializer = TransactionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            transaction = update_transaction(pk, request.user, **serializer.validated_data)
            return Response(TransactionSerializer(transaction).data)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        tags=['Transactions'],
        summary='Remover transação (soft-delete)',
        responses={204: None},
    )
    def delete(self, request, pk):
        """Realiza soft-delete da transação; retorna 204 sem corpo."""
        try:
            deactivate_transaction(pk, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)


class RecurringTransactionCreateAPIView(APIView):
    """
    POST /api/v1/transactions/recurring/  — cria transação recorrente; retorna 201.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Transactions'],
        summary='Criar transação recorrente',
        request=RecurringTransactionCreateSerializer,
        responses={201: TransactionSerializer},
    )
    def post(self, request):
        """Cria transação recorrente extraindo frequency do payload e retorna 201."""
        serializer = RecurringTransactionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = serializer.validated_data.copy()
            frequency = data.pop("frequency")
            transaction_data = data
            transaction = create_recurring_transaction(request.user, transaction_data, frequency)
            return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)


class RecurringTransactionDeleteAPIView(APIView):
    """
    DELETE /api/v1/transactions/recurring/<uuid:pk>/  — remove transação recorrente; retorna 204.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Transactions'],
        summary='Remover transação recorrente',
        responses={204: None},
    )
    def delete(self, request, pk):
        """Remove transação recorrente e todas as suas ocorrências futuras; retorna 204."""
        try:
            delete_recurring_transaction(pk, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)


class InstallmentTransactionCreateAPIView(APIView):
    """
    POST /api/v1/transactions/installment/  — cria transação parcelada; retorna 201.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Transactions'],
        summary='Criar transação parcelada',
        request=InstallmentTransactionCreateSerializer,
        responses={201: TransactionSerializer},
    )
    def post(self, request):
        """Cria transação parcelada extraindo total_installments do payload e retorna 201."""
        serializer = InstallmentTransactionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = serializer.validated_data.copy()
            total_installments = data.pop("total_installments")
            transaction_data = data
            transaction = create_installment_transaction(request.user, transaction_data, total_installments)
            return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)


class InstallmentListAPIView(APIView):
    """
    GET /api/v1/transactions/<uuid:pk>/installments/  — lista parcelas de uma transação.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Transactions'],
        summary='Listar parcelas da transação',
        responses={200: InstallmentSerializer(many=True)},
    )
    def get(self, request, pk):
        """Retorna lista de parcelas da transação especificada."""
        try:
            installments = get_installments(pk, request.user)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        serializer = InstallmentSerializer(installments, many=True)
        return Response(serializer.data)


class TransactionStatusUpdateAPIView(APIView):
    """
    PATCH /api/v1/transactions/<uuid:pk>/status/  — atualiza status da transação.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Transactions'],
        summary='Atualizar status da transação',
        request=inline_serializer(
            name='StatusUpdateRequest',
            fields={'status': drf_serializers.CharField(help_text='Novo status: pendente ou pago')},
        ),
        responses={200: TransactionSerializer},
    )
    def patch(self, request, pk):
        """Atualiza o status da transação (pendente/pago) e retorna representação atualizada."""
        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "O campo 'status' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            transaction = update_status(pk, request.user, new_status)
            return Response(TransactionSerializer(transaction).data)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
