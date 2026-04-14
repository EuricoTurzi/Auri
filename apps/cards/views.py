"""
Views SSR para o app cards — listagem, criação, detalhe, edição e exclusão de cartões.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.views import View

from .services import create_card, update_card, deactivate_card
from .selectors import (
    get_available_limit,
    get_card_by_id,
    get_card_transactions,
    get_card_transactions_summary,
    get_month_period,
    get_user_cards,
)


def _campo_opcional_inteiro(valor):
    """Converte string de POST para inteiro ou None se vazia."""
    if valor is None or valor.strip() == "":
        return None
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def _campo_opcional_decimal(valor):
    """Converte string de POST para Decimal (via str) ou None se vazia."""
    if valor is None or valor.strip() == "":
        return None
    valor = valor.strip()
    if valor == "":
        return None
    return valor  # O model/ORM faz a conversão para Decimal


class CardListView(LoginRequiredMixin, View):
    """Lista os cartões ativos do usuário com o limite disponível de cada um."""

    def get(self, request):
        cards_com_limite = [
            {"card": card, "available_limit": get_available_limit(card)}
            for card in get_user_cards(request.user)
        ]
        return render(request, "cards/card_list.html", {"cards_com_limite": cards_com_limite})


class CardCreateView(LoginRequiredMixin, View):
    """Formulário de criação de um novo cartão."""

    def get(self, request):
        return render(request, "cards/card_form.html", {"action": "create"})

    def post(self, request):
        try:
            create_card(
                user=request.user,
                name=request.POST.get("name", ""),
                brand=request.POST.get("brand", ""),
                last_four_digits=request.POST.get("last_four_digits", ""),
                card_type=request.POST.get("card_type", ""),
                credit_limit=_campo_opcional_decimal(request.POST.get("credit_limit")),
                billing_close_day=_campo_opcional_inteiro(request.POST.get("billing_close_day")),
                billing_due_day=_campo_opcional_inteiro(request.POST.get("billing_due_day")),
            )
            messages.success(request, "Cartão criado com sucesso.")
            return redirect("cards:list")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
            return render(request, "cards/card_form.html", {"action": "create"})


class CardDetailView(LoginRequiredMixin, View):
    """Exibe os detalhes de um cartão, limite disponível, transações do mês
    selecionado e resumo agregado (entradas, saídas e saldo líquido)."""

    def get(self, request, pk):
        try:
            card = get_card_by_id(pk, request.user)
        except PermissionError:
            messages.error(request, "Cartão não encontrado.")
            return redirect("cards:list")

        month_str = request.GET.get("month", "")
        billing_period = get_month_period(month_str)

        available_limit = get_available_limit(card)
        transactions = get_card_transactions(pk, request.user, billing_period=billing_period)
        resumo = get_card_transactions_summary(pk, request.user, billing_period=billing_period)

        month_selected = month_str if month_str else billing_period[0].strftime("%Y-%m")

        return render(request, "cards/card_detail.html", {
            "card": card,
            "available_limit": available_limit,
            "transactions": transactions,
            "resumo": resumo,
            "month_selected": month_selected,
            "billing_period": billing_period,
        })


class CardUpdateView(LoginRequiredMixin, View):
    """Formulário de edição de um cartão existente."""

    def get(self, request, pk):
        try:
            card = get_card_by_id(pk, request.user)
        except PermissionError:
            messages.error(request, "Cartão não encontrado.")
            return redirect("cards:list")
        return render(request, "cards/card_form.html", {"card": card, "action": "edit"})

    def post(self, request, pk):
        campos = {
            k: v
            for k, v in request.POST.items()
            if k != "csrfmiddlewaretoken"
        }

        # Normaliza campos opcionais
        if "credit_limit" in campos:
            campos["credit_limit"] = _campo_opcional_decimal(campos["credit_limit"])
        if "billing_close_day" in campos:
            campos["billing_close_day"] = _campo_opcional_inteiro(campos["billing_close_day"])
        if "billing_due_day" in campos:
            campos["billing_due_day"] = _campo_opcional_inteiro(campos["billing_due_day"])

        try:
            update_card(pk, request.user, **campos)
            messages.success(request, "Cartão atualizado com sucesso.")
            return redirect("cards:list")
        except (ValidationError, PermissionError) as e:
            messages.error(request, str(e))
            return redirect("cards:list")


class CardDeleteView(LoginRequiredMixin, View):
    """Soft-delete de um cartão via POST."""

    def post(self, request, pk):
        try:
            deactivate_card(pk, request.user)
            messages.success(request, "Cartão desativado com sucesso.")
        except PermissionError as e:
            messages.error(request, str(e))
        return redirect("cards:list")
