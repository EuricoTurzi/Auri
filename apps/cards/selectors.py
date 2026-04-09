"""
Selectors para o app cards — consultas de leitura e cálculo de limite.
"""
import calendar
import datetime
from decimal import Decimal

from django.apps import apps as django_apps
from django.db.models import Sum

from apps.cards.models import Card


def get_user_cards(user, active_only=True):
    """
    Retorna cartões do usuário.
    Se active_only=True, filtra apenas cartões ativos (is_active=True).
    """
    qs = Card.objects.filter(user=user)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def get_card_by_id(card_id, user):
    """
    Retorna cartão por ID validando ownership.
    Levanta PermissionError se não encontrado ou não pertence ao usuário.
    """
    try:
        return Card.objects.get(id=card_id, user=user, is_active=True)
    except Card.DoesNotExist:
        raise PermissionError("Cartão não encontrado ou sem permissão de acesso.")


def _get_current_billing_period(card):
    """
    Calcula o período da fatura atual com base no billing_close_day do cartão.

    - Se billing_close_day for None, usa o mês corrente (dia 1 ao último dia).
    - Caso contrário, o período é do (billing_close_day do mês anterior + 1) até
      o billing_close_day do mês atual.

    Retorna uma tupla (data_inicio, data_fim) do tipo datetime.date.
    """
    today = datetime.date.today()

    if card.billing_close_day is None:
        inicio = today.replace(day=1)
        ultimo_dia = calendar.monthrange(today.year, today.month)[1]
        fim = today.replace(day=ultimo_dia)
        return inicio, fim

    close_day = card.billing_close_day

    # Dia de fechamento no mês atual
    ultimo_dia_mes_atual = calendar.monthrange(today.year, today.month)[1]
    close_day_atual = min(close_day, ultimo_dia_mes_atual)
    data_fechamento_atual = today.replace(day=close_day_atual)

    # Calcular o mês anterior
    if today.month == 1:
        mes_anterior = 12
        ano_anterior = today.year - 1
    else:
        mes_anterior = today.month - 1
        ano_anterior = today.year

    ultimo_dia_mes_anterior = calendar.monthrange(ano_anterior, mes_anterior)[1]
    close_day_anterior = min(close_day, ultimo_dia_mes_anterior)
    data_fechamento_anterior = datetime.date(ano_anterior, mes_anterior, close_day_anterior)

    # Início = dia seguinte ao fechamento do mês anterior
    data_inicio = data_fechamento_anterior + datetime.timedelta(days=1)
    data_fim = data_fechamento_atual

    return data_inicio, data_fim


def _get_current_billing_period_spent(card, Transaction):
    """
    Calcula o total gasto no período de fatura atual do cartão,
    considerando apenas transações de saída vinculadas ao cartão.
    """
    data_inicio, data_fim = _get_current_billing_period(card)

    total = (
        Transaction.objects.filter(
            card=card,
            transaction_type="saida",
            date__gte=data_inicio,
            date__lte=data_fim,
        )
        .aggregate(total=Sum("amount"))
        ["total"]
    )

    return total or Decimal("0")


def get_available_limit(card):
    """
    Calcula o limite disponível do cartão de crédito.

    Retorna None para cartões de débito ou sem credit_limit definido.
    Usa import defensivo para o model Transaction, que pode ainda não existir.
    """
    if card.card_type != "credito" or not card.credit_limit:
        return None

    try:
        Transaction = django_apps.get_model("transactions", "Transaction")
        used = _get_current_billing_period_spent(card, Transaction)
        available = card.credit_limit - used
        return max(available, Decimal("0"))
    except LookupError:
        # transactions ainda não implementado
        return card.credit_limit


def get_card_transactions(card_id, user, billing_period=None):
    """
    Retorna transações vinculadas ao cartão do usuário.
    Valida ownership do cartão antes de consultar transações.

    Parâmetros:
        card_id: UUID do cartão.
        user: instância do usuário proprietário.
        billing_period: tupla opcional (date_start, date_end) para filtrar por período.

    Retorna QuerySet de transações ou lista vazia se o model Transaction não existir.
    Levanta PermissionError se o cartão não pertencer ao usuário.
    """
    # Valida ownership — levanta PermissionError se não encontrado
    card = get_card_by_id(card_id, user)

    try:
        Transaction = django_apps.get_model("transactions", "Transaction")
    except LookupError:
        # transactions ainda não implementado — retorna queryset vazio compatível
        return Card.objects.none()

    qs = Transaction.objects.filter(card=card)

    if billing_period is not None:
        date_start, date_end = billing_period
        qs = qs.filter(date__gte=date_start, date__lte=date_end)

    return qs
