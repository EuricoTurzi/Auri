"""
Selectors para o app reports — consultas agregadas para dashboard e exportação.
Todas as queries garantem isolamento por usuário (tenant isolation).
"""
from decimal import Decimal

from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth

from apps.reports.models import ScheduledReport


def _apply_filters(qs, filters):
    """Aplica filtros comuns ao queryset de transações."""
    if not filters:
        return qs

    if filters.get("period_start"):
        qs = qs.filter(date__gte=filters["period_start"])

    if filters.get("period_end"):
        qs = qs.filter(date__lte=filters["period_end"])

    if filters.get("category_ids"):
        qs = qs.filter(category_id__in=filters["category_ids"])

    if filters.get("type"):
        qs = qs.filter(type=filters["type"])

    if filters.get("card_ids"):
        qs = qs.filter(card_id__in=filters["card_ids"])

    return qs


def get_dashboard_data(user, filters=None):
    """
    Retorna dados agregados do dashboard para o usuário.

    Retorna dict com:
        - total_entradas: Decimal
        - total_saidas: Decimal
        - saldo: Decimal
        - gastos_por_categoria: list[{categoria, total}]
        - evolucao_temporal: list[{mes, entradas, saidas}]
        - gastos_por_cartao: list[{cartao, total}]
    """
    from django.apps import apps as django_apps
    Transaction = django_apps.get_model("transactions", "Transaction")

    qs = Transaction.objects.filter(user=user, is_active=True)
    qs = _apply_filters(qs, filters)

    # Totais
    total_entradas = qs.filter(type="entrada").aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    total_saidas = qs.filter(type="saida").aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    saldo = total_entradas - total_saidas

    # Gastos por categoria (apenas saídas)
    gastos_por_categoria = list(
        qs.filter(type="saida")
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    gastos_por_categoria = [
        {"categoria": item["category__name"], "total": item["total"]}
        for item in gastos_por_categoria
    ]

    # Evolução temporal (agrupado por mês)
    meses_data = (
        qs.annotate(mes=TruncMonth("date"))
        .values("mes")
        .annotate(
            entradas=Sum("amount", filter=Q(type="entrada")),
            saidas=Sum("amount", filter=Q(type="saida")),
        )
        .order_by("mes")
    )
    evolucao_temporal = [
        {
            "mes": item["mes"].strftime("%Y-%m"),
            "entradas": item["entradas"] or Decimal("0"),
            "saidas": item["saidas"] or Decimal("0"),
        }
        for item in meses_data
    ]

    # Gastos por cartão (apenas saídas com cartão)
    gastos_por_cartao = list(
        qs.filter(type="saida", card__isnull=False)
        .values("card__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    gastos_por_cartao = [
        {"cartao": item["card__name"], "total": item["total"]}
        for item in gastos_por_cartao
    ]

    return {
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo": saldo,
        "gastos_por_categoria": gastos_por_categoria,
        "evolucao_temporal": evolucao_temporal,
        "gastos_por_cartao": gastos_por_cartao,
    }


def get_filtered_transactions(user, filters):
    """
    Retorna transações filtradas para exportação.

    Filtros suportados: period_start, period_end, category_ids, type, card_ids.
    """
    from django.apps import apps as django_apps
    Transaction = django_apps.get_model("transactions", "Transaction")

    qs = Transaction.objects.filter(user=user, is_active=True)
    qs = _apply_filters(qs, filters)
    return qs


def get_user_scheduled_reports(user):
    """Retorna relatórios agendados ativos do usuário."""
    return ScheduledReport.objects.filter(user=user, is_active=True)
