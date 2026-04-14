"""
Views SSR para o app transactions — CRUD de transações usando Django Templates.
Todas as views exigem autenticação via LoginRequiredMixin.
"""

from decimal import Decimal, InvalidOperation

from django.apps import apps as django_apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views import View

from apps.transactions.selectors import (
    get_installments,
    get_transaction_by_id,
    get_user_transactions,
)
from apps.transactions.services import (
    create_installment_transaction,
    create_recurring_transaction,
    create_transaction,
    deactivate_transaction,
    delete_recurring_transaction,
    update_transaction,
)


class TransactionListView(LoginRequiredMixin, View):
    """Lista as transações do usuário com suporte a filtros via GET params."""

    template_name = "transactions/transaction_list.html"

    def get(self, request):
        from datetime import date
        import calendar

        # Define data inicial/final padrão (Mês atual) se não houver filtro na URL
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        ultimo_dia = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])

        # Extrai filtros dos parâmetros de query
        filtros = {
            "type": request.GET.get("type", ""),
            "category_id": request.GET.get("category_id", ""),
            "card_id": request.GET.get("card_id", ""),
            "date_start": request.GET.get("date_start", primeiro_dia.strftime("%Y-%m-%d")),
            "date_end": request.GET.get("date_end", ultimo_dia.strftime("%Y-%m-%d")),
            "status": request.GET.get("status", ""),
        }

        transacoes = get_user_transactions(request.user, filtros)

        Category = django_apps.get_model("categories", "Category")
        Card = django_apps.get_model("cards", "Card")

        categorias = Category.objects.filter(user=request.user, is_active=True)
        cartoes = Card.objects.filter(user=request.user, is_active=True)

        contexto = {
            "transacoes": transacoes,
            "filtros": filtros,
            "categorias": categorias,
            "cartoes": cartoes,
        }
        return render(request, self.template_name, contexto)


class TransactionCreateView(LoginRequiredMixin, View):
    """Cria uma nova transação — simples, recorrente ou parcelada."""

    template_name = "transactions/transaction_form.html"

    def _build_context(self, request):
        """Monta contexto base com categorias, cartões e data atual."""
        from datetime import date

        Category = django_apps.get_model("categories", "Category")
        Card = django_apps.get_model("cards", "Card")

        categorias = Category.objects.filter(user=request.user, is_active=True)
        cartoes = Card.objects.filter(user=request.user, is_active=True)

        return {
            "categorias": categorias,
            "cartoes": cartoes,
            "hoje": date.today(),
        }

    def get(self, request):
        contexto = self._build_context(request)
        return render(request, self.template_name, contexto)

    def post(self, request):
        contexto = self._build_context(request)
        post = request.POST

        # Coleta dados do formulário
        name = post.get("name", "").strip()
        description = post.get("description", "").strip() or None
        status = post.get("status", "pendente")
        type_ = post.get("type", "")
        category_id = post.get("category_id", "") or None
        card_id = post.get("card_id", "") or None
        date_str = post.get("date", "")
        due_date_str = post.get("due_date", "") or None

        # Converte amount para Decimal
        try:
            amount = Decimal(post.get("amount", "0"))
        except InvalidOperation:
            contexto["error"] = "Valor inválido."
            return render(request, self.template_name, contexto)

        # Converte datas
        from datetime import datetime

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
        except ValueError:
            contexto["error"] = "Data inválida."
            return render(request, self.template_name, contexto)

        try:
            due_date = (
                datetime.strptime(due_date_str, "%Y-%m-%d").date() if due_date_str else None
            )
        except ValueError:
            contexto["error"] = "Data de vencimento inválida."
            return render(request, self.template_name, contexto)

        # Valida campos obrigatórios antes de chamar services
        if not category_id:
            contexto["error"] = "Categoria é obrigatória."
            return render(request, self.template_name, contexto)

        if not date:
            contexto["error"] = "Data é obrigatória."
            return render(request, self.template_name, contexto)

        # Flags de recorrência / parcelamento
        is_recurring = post.get("is_recurring") == "on"
        frequency = post.get("frequency", "").strip() or None
        is_installment = post.get("is_installment") == "on"
        total_installments_str = post.get("total_installments", "").strip()

        # Valida campos obrigatórios das flags
        if is_recurring and not frequency:
            contexto["error"] = "Frequência é obrigatória para transações recorrentes."
            return render(request, self.template_name, contexto)

        if is_installment and not total_installments_str:
            contexto["error"] = "Número de parcelas é obrigatório para transações parceladas."
            return render(request, self.template_name, contexto)

        # Dados base da transação
        transaction_data = {
            "name": name,
            "description": description,
            "amount": amount,
            "type": type_,
            "category_id": category_id,
            "date": date,
            "due_date": due_date,
            "status": status,
        }
        if card_id:
            transaction_data["card_id"] = card_id

        try:
            if is_recurring:
                # Transação recorrente
                create_recurring_transaction(
                    user=request.user,
                    transaction_data=transaction_data,
                    frequency=frequency,
                )
            elif is_installment:
                # Transação parcelada
                try:
                    total_installments = int(total_installments_str)
                except ValueError:
                    contexto["error"] = "Número de parcelas inválido."
                    return render(request, self.template_name, contexto)

                create_installment_transaction(
                    user=request.user,
                    transaction_data=transaction_data,
                    total_installments=total_installments,
                )
            else:
                # Transação simples
                create_transaction(
                    user=request.user,
                    **transaction_data,
                )
        except (ValidationError, PermissionError) as exc:
            contexto["error"] = str(exc)
            return render(request, self.template_name, contexto)

        return redirect("transactions:list")


class TransactionDetailView(LoginRequiredMixin, View):
    """Exibe os detalhes de uma transação, incluindo parcelas se parcelada."""

    template_name = "transactions/transaction_detail.html"

    def get(self, request, pk):
        try:
            transacao = get_transaction_by_id(pk, request.user)
        except PermissionError as exc:
            return render(request, self.template_name, {"error": str(exc)})

        # Busca parcelas apenas se a transação for parcelada
        parcelas = []
        if transacao.is_installment:
            try:
                parcelas = get_installments(pk, request.user)
            except PermissionError:
                parcelas = []

        contexto = {
            "transacao": transacao,
            "installments": parcelas,
        }
        return render(request, self.template_name, contexto)


class TransactionUpdateView(LoginRequiredMixin, View):
    """Edita uma transação existente — apenas campos fornecidos são atualizados."""

    template_name = "transactions/transaction_form.html"

    def _build_context(self, request, transacao=None):
        """Monta contexto com categorias, cartões e transação pré-populada."""
        from datetime import date

        Category = django_apps.get_model("categories", "Category")
        Card = django_apps.get_model("cards", "Card")

        categorias = Category.objects.filter(user=request.user, is_active=True)
        cartoes = Card.objects.filter(user=request.user, is_active=True)

        return {
            "categorias": categorias,
            "cartoes": cartoes,
            "transacao": transacao,
            "editando": True,
            "hoje": date.today(),
        }

    def get(self, request, pk):
        try:
            transacao = get_transaction_by_id(pk, request.user)
        except PermissionError as exc:
            return render(request, self.template_name, {"error": str(exc)})

        contexto = self._build_context(request, transacao)
        return render(request, self.template_name, contexto)

    def post(self, request, pk):
        try:
            transacao = get_transaction_by_id(pk, request.user)
        except PermissionError as exc:
            return render(request, self.template_name, {"error": str(exc)})

        contexto = self._build_context(request, transacao)
        post = request.POST

        # Monta kwargs apenas com campos que foram enviados e não estão vazios
        kwargs = {}

        for campo in ("name", "description", "type", "status"):
            valor = post.get(campo, "").strip()
            if valor:
                kwargs[campo] = valor

        # Campos opcionais que podem ser limpos
        category_id = post.get("category_id", "").strip()
        if category_id:
            kwargs["category_id"] = category_id

        card_id = post.get("card_id", "").strip()
        # Permite explicitamente limpar o cartão enviando string vazia
        if "card_id" in post:
            kwargs["card_id"] = card_id if card_id else None

        amount_str = post.get("amount", "").strip()
        if amount_str:
            try:
                kwargs["amount"] = Decimal(amount_str)
            except InvalidOperation:
                contexto["error"] = "Valor inválido."
                return render(request, self.template_name, contexto)

        from datetime import datetime

        date_str = post.get("date", "").strip()
        if date_str:
            try:
                kwargs["date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                contexto["error"] = "Data inválida."
                return render(request, self.template_name, contexto)

        due_date_str = post.get("due_date", "").strip()
        if "due_date" in post:
            if due_date_str:
                try:
                    kwargs["due_date"] = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    contexto["error"] = "Data de vencimento inválida."
                    return render(request, self.template_name, contexto)
            else:
                kwargs["due_date"] = None

        try:
            update_transaction(pk, request.user, **kwargs)
        except (ValidationError, PermissionError) as exc:
            contexto["error"] = str(exc)
            return render(request, self.template_name, contexto)

        return redirect("transactions:list")


class TransactionDeleteView(LoginRequiredMixin, View):
    """Desativa (soft-delete) ou exclui uma transação recorrente via POST."""

    def post(self, request, pk):
        try:
            transacao = get_transaction_by_id(pk, request.user)
        except PermissionError:
            return redirect("transactions:list")

        try:
            if transacao.is_recurring:
                delete_recurring_transaction(pk, request.user)
            else:
                deactivate_transaction(pk, request.user)
        except (ValidationError, PermissionError) as exc:
            from django.contrib import messages
            messages.error(request, str(exc))

        return redirect("transactions:list")
