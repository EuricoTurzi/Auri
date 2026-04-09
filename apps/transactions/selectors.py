"""
Selectors para o app transactions — consultas de leitura sobre transações e parcelas.
Todas as queries garantem isolamento por usuário (tenant isolation).
"""

from apps.transactions.models import Installment, Transaction


def get_user_transactions(user, filters=None):
    """
    Retorna transações ativas do usuário.

    Parâmetros opcionais via dict `filters`:
        - type: "entrada" ou "saida"
        - category_id: UUID da categoria
        - card_id: UUID do cartão
        - date_start: data inicial (inclusiva)
        - date_end: data final (inclusiva)
        - status: "pendente" ou "pago"

    Retorna QuerySet de Transaction.
    """
    qs = Transaction.objects.filter(user=user, is_active=True)

    if not filters:
        return qs

    if "type" in filters and filters["type"]:
        qs = qs.filter(type=filters["type"])

    if "category_id" in filters and filters["category_id"]:
        qs = qs.filter(category_id=filters["category_id"])

    if "card_id" in filters and filters["card_id"]:
        qs = qs.filter(card_id=filters["card_id"])

    if "date_start" in filters and filters["date_start"]:
        qs = qs.filter(date__gte=filters["date_start"])

    if "date_end" in filters and filters["date_end"]:
        qs = qs.filter(date__lte=filters["date_end"])

    if "status" in filters and filters["status"]:
        qs = qs.filter(status=filters["status"])

    return qs


def get_transaction_by_id(transaction_id, user):
    """
    Retorna uma transação por ID validando ownership.
    Levanta PermissionError se não encontrada ou não pertence ao usuário.
    """
    try:
        return Transaction.objects.get(id=transaction_id, user=user, is_active=True)
    except Transaction.DoesNotExist:
        raise PermissionError("Transação não encontrada ou sem permissão de acesso.")


def get_installments(transaction_id, user):
    """
    Retorna as parcelas de uma transação específica.
    Valida ownership da transação antes de consultar as parcelas.
    Levanta PermissionError se a transação não for encontrada ou não pertencer ao usuário.
    """
    # Valida ownership — levanta PermissionError se não encontrada
    get_transaction_by_id(transaction_id, user)

    return Installment.objects.filter(parent_transaction_id=transaction_id)


def get_recurring_transactions(user):
    """
    Retorna transações recorrentes ativas do usuário.
    Retorna apenas transações pai (recurring_parent=None), ou seja,
    os registros originais — não as ocorrências geradas.
    """
    return Transaction.objects.filter(
        user=user,
        is_active=True,
        is_recurring=True,
        recurring_parent__isnull=True,
    )
