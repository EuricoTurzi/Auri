"""
API Views DRF para o app reports — endpoints REST com autenticação JWT.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .serializers import (
    DashboardSerializer,
    DashboardFilterSerializer,
    ScheduledReportSerializer,
    ScheduledReportCreateUpdateSerializer,
)
from .selectors import get_dashboard_data, get_filtered_transactions, get_user_scheduled_reports
from .services import (
    create_scheduled_report,
    update_scheduled_report,
    deactivate_scheduled_report,
    export_csv,
    export_xlsx,
    export_pdf,
)


class DashboardAPIView(APIView):
    """GET /api/v1/reports/dashboard/ — retorna dados do dashboard com filtros."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Reports'],
        summary='Dados do dashboard',
        parameters=[
            OpenApiParameter(name='period_start', type=str, required=False, description='Data inicial (YYYY-MM-DD)'),
            OpenApiParameter(name='period_end', type=str, required=False, description='Data final (YYYY-MM-DD)'),
            OpenApiParameter(name='type', type=str, required=False, description='Filtro por tipo (entrada/saida)'),
            OpenApiParameter(name='category_ids', type={'type': 'array', 'items': {'type': 'string', 'format': 'uuid'}}, required=False, description='UUIDs de categorias'),
            OpenApiParameter(name='card_ids', type={'type': 'array', 'items': {'type': 'string', 'format': 'uuid'}}, required=False, description='UUIDs de cartões'),
        ],
        responses={200: DashboardSerializer},
    )
    def get(self, request):
        filter_serializer = DashboardFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        filters = filter_serializer.validated_data
        data = get_dashboard_data(request.user, filters if filters else None)
        serializer = DashboardSerializer(data)
        return Response(serializer.data)


class ExportAPIView(APIView):
    """GET /api/v1/reports/export/<format>/ — retorna arquivo exportado."""

    permission_classes = [IsAuthenticated]
    FORMATOS_VALIDOS = {"csv", "xlsx", "pdf"}

    @extend_schema(
        tags=['Reports'],
        summary='Exportar relatório (csv, xlsx ou pdf)',
        parameters=[
            OpenApiParameter(name='export_format', type=str, location=OpenApiParameter.PATH, description='Formato: csv, xlsx ou pdf'),
            OpenApiParameter(name='period_start', type=str, required=False, description='Data inicial (YYYY-MM-DD)'),
            OpenApiParameter(name='period_end', type=str, required=False, description='Data final (YYYY-MM-DD)'),
            OpenApiParameter(name='type', type=str, required=False, description='Filtro por tipo (entrada/saida)'),
        ],
        responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request, export_format):
        if export_format not in self.FORMATOS_VALIDOS:
            return Response(
                {"detail": "Formato inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filter_serializer = DashboardFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        qs = get_filtered_transactions(request.user, filter_serializer.validated_data)

        if export_format == "csv":
            return export_csv(qs)
        elif export_format == "xlsx":
            return export_xlsx(qs)
        else:
            return export_pdf(qs, request.user, filter_serializer.validated_data)


class ScheduledReportListCreateAPIView(APIView):
    """
    GET  /api/v1/reports/scheduled/     — lista relatórios agendados.
    POST /api/v1/reports/scheduled/     — cria relatório agendado.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Reports'],
        summary='Listar relatórios agendados',
        responses={200: ScheduledReportSerializer(many=True)},
    )
    def get(self, request):
        reports = get_user_scheduled_reports(request.user)
        serializer = ScheduledReportSerializer(reports, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Reports'],
        summary='Criar relatório agendado',
        request=ScheduledReportCreateUpdateSerializer,
        responses={201: ScheduledReportSerializer},
    )
    def post(self, request):
        serializer = ScheduledReportCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        report = create_scheduled_report(
            user=request.user,
            **serializer.validated_data,
        )
        return Response(
            ScheduledReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )


class ScheduledReportDetailAPIView(APIView):
    """
    GET    /api/v1/reports/scheduled/<uuid:pk>/ — detalhe.
    PUT    /api/v1/reports/scheduled/<uuid:pk>/ — atualiza.
    DELETE /api/v1/reports/scheduled/<uuid:pk>/ — soft-delete.
    """

    permission_classes = [IsAuthenticated]

    def _get_report(self, pk, user):
        from .models import ScheduledReport
        try:
            report = ScheduledReport.objects.get(id=pk, is_active=True)
        except ScheduledReport.DoesNotExist:
            return None
        if report.user != user:
            return None
        return report

    @extend_schema(
        tags=['Reports'],
        summary='Detalhe do relatório agendado',
        responses={200: ScheduledReportSerializer},
    )
    def get(self, request, pk):
        report = self._get_report(pk, request.user)
        if not report:
            return Response(
                {"detail": "Relatório não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ScheduledReportSerializer(report).data)

    @extend_schema(
        tags=['Reports'],
        summary='Atualizar relatório agendado',
        request=ScheduledReportCreateUpdateSerializer,
        responses={200: ScheduledReportSerializer},
    )
    def put(self, request, pk):
        serializer = ScheduledReportCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            report = update_scheduled_report(pk, request.user, **serializer.validated_data)
            return Response(ScheduledReportSerializer(report).data)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        tags=['Reports'],
        summary='Remover relatório agendado (soft-delete)',
        responses={204: None},
    )
    def delete(self, request, pk):
        try:
            deactivate_scheduled_report(pk, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
