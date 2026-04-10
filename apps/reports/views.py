"""
Views SSR para o app reports — dashboard, exportação e CRUD de agendamentos.
Todas as views exigem autenticação via LoginRequiredMixin.
"""
from django.apps import apps as django_apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views import View

from apps.reports.selectors import get_dashboard_data, get_filtered_transactions, get_user_scheduled_reports
from apps.reports.services import (
    create_scheduled_report,
    deactivate_scheduled_report,
    export_csv,
    export_xlsx,
    export_pdf,
)


def _extract_filters(request):
    """Extrai filtros dos parâmetros GET."""
    filters = {}
    period_start = request.GET.get("period_start", "")
    period_end = request.GET.get("period_end", "")
    type_ = request.GET.get("type", "")
    category_ids = request.GET.getlist("category_ids")
    card_ids = request.GET.getlist("card_ids")

    if period_start:
        filters["period_start"] = period_start
    if period_end:
        filters["period_end"] = period_end
    if type_:
        filters["type"] = type_
    if category_ids:
        filters["category_ids"] = category_ids
    if card_ids:
        filters["card_ids"] = card_ids

    return filters


class DashboardView(LoginRequiredMixin, View):
    """Dashboard com gráficos e filtros."""

    template_name = "reports/dashboard.html"

    def get(self, request):
        filters = _extract_filters(request)
        dashboard = get_dashboard_data(request.user, filters)

        Category = django_apps.get_model("categories", "Category")
        Card = django_apps.get_model("cards", "Card")
        categorias = Category.objects.filter(user=request.user, is_active=True)
        cartoes = Card.objects.filter(user=request.user, is_active=True)

        contexto = {
            "dashboard": dashboard,
            "filtros": filters,
            "categorias": categorias,
            "cartoes": cartoes,
        }
        return render(request, self.template_name, contexto)


class ExportView(LoginRequiredMixin, View):
    """Exporta dados filtrados no formato solicitado."""

    FORMATOS_VALIDOS = {"csv", "xlsx", "pdf"}

    def get(self, request, format):
        if format not in self.FORMATOS_VALIDOS:
            return HttpResponseBadRequest("Formato inválido.")

        filters = _extract_filters(request)
        qs = get_filtered_transactions(request.user, filters)

        if format == "csv":
            return export_csv(qs)
        elif format == "xlsx":
            return export_xlsx(qs)
        else:
            return export_pdf(qs, request.user, filters)


class ScheduledReportListView(LoginRequiredMixin, View):
    """Lista relatórios agendados do usuário."""

    template_name = "reports/scheduled_list.html"

    def get(self, request):
        reports = get_user_scheduled_reports(request.user)
        return render(request, self.template_name, {"reports": reports})


class ScheduledReportCreateView(LoginRequiredMixin, View):
    """Formulário de criação de relatório agendado."""

    template_name = "reports/scheduled_form.html"

    def get(self, request):
        Category = django_apps.get_model("categories", "Category")
        Card = django_apps.get_model("cards", "Card")
        categorias = Category.objects.filter(user=request.user, is_active=True)
        cartoes = Card.objects.filter(user=request.user, is_active=True)
        return render(request, self.template_name, {
            "categorias": categorias,
            "cartoes": cartoes,
        })

    def post(self, request):
        name = request.POST.get("name", "").strip()
        frequency = request.POST.get("frequency", "")
        export_format = request.POST.get("export_format", "")

        # Monta filtros do formulário
        filters = {}
        period_start = request.POST.get("period_start", "")
        period_end = request.POST.get("period_end", "")
        type_ = request.POST.get("type", "")
        category_ids = request.POST.getlist("category_ids")
        card_ids = request.POST.getlist("card_ids")

        if period_start:
            filters["period_start"] = period_start
        if period_end:
            filters["period_end"] = period_end
        if type_:
            filters["type"] = type_
        if category_ids:
            filters["category_ids"] = category_ids
        if card_ids:
            filters["card_ids"] = card_ids

        create_scheduled_report(
            user=request.user,
            name=name,
            frequency=frequency,
            export_format=export_format,
            filters=filters,
        )
        return redirect("reports:scheduled_list")


class ScheduledReportDeleteView(LoginRequiredMixin, View):
    """Soft-delete de relatório agendado via POST."""

    def post(self, request, pk):
        try:
            deactivate_scheduled_report(pk, request.user)
        except PermissionError:
            pass
        return redirect("reports:scheduled_list")
