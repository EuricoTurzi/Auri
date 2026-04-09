from django.apps import apps as django_apps
from django.core.exceptions import ValidationError

from .models import Transaction

# Campos que podem ser atualizados via update_transaction
CAMPOS_PERMITIDOS = {
    "name",
    "description",
    "amount",
    "type",
    "status",
    "category_id",
    "card_id",
    "date",
    "due_date",
}

# Tipos e status válidos
TIPOS_VALIDOS = {choice[0] for choice in Transaction.TYPE_CHOICES}
STATUS_VALIDOS = {choice[0] for choice in Transaction.STATUS_CHOICES}


def _validar_categoria(category_id, user):
    """Valida que a categoria existe e pertence ao usuário.

    Levanta PermissionError se não encontrada ou não pertencer ao usuário.
    """
    Category = django_apps.get_model("categories", "Category")
    try:
        categoria = Category.objects.get(id=category_id, is_active=True)
    except Category.DoesNotExist:
        raise PermissionError("Categoria não encontrada.")

    if categoria.user != user:
        raise PermissionError("Sem permissão para usar esta categoria.")

    return categoria


def _validar_cartao(card_id, user):
    """Valida que o cartão existe e pertence ao usuário.

    Levanta PermissionError se não encontrado ou não pertencer ao usuário.
    """
    Card = django_apps.get_model("cards", "Card")
    try:
        cartao = Card.objects.get(id=card_id, is_active=True)
    except Card.DoesNotExist:
        raise PermissionError("Cartão não encontrado.")

    if cartao.user != user:
        raise PermissionError("Sem permissão para usar este cartão.")

    return cartao


def create_transaction(
    user,
    name,
    amount,
    type,
    category_id,
    date,
    description=None,
    card_id=None,
    due_date=None,
    status="pendente",
):
    """Cria uma nova transação para o usuário.

    Valida:
    - Tipo deve ser "entrada" ou "saida".
    - Categoria deve existir e pertencer ao usuário.
    - Cartão (se fornecido) deve existir e pertencer ao usuário.
    - Valor deve ser maior que zero.

    Levanta ValidationError para dados inválidos e PermissionError para falhas de ownership.
    """
    # Valida tipo
    if type not in TIPOS_VALIDOS:
        raise ValidationError(f"Tipo inválido. Escolha entre: {', '.join(TIPOS_VALIDOS)}.")

    # Valida amount
    if amount is None or amount <= 0:
        raise ValidationError("O valor da transação deve ser maior que zero.")

    # Valida status
    if status not in STATUS_VALIDOS:
        raise ValidationError(f"Status inválido. Escolha entre: {', '.join(STATUS_VALIDOS)}.")

    # Valida categoria (ownership)
    categoria = _validar_categoria(category_id, user)

    # Valida cartão (ownership), se fornecido
    cartao = None
    if card_id is not None:
        cartao = _validar_cartao(card_id, user)

    return Transaction.objects.create(
        user=user,
        name=name,
        description=description,
        amount=amount,
        type=type,
        status=status,
        category=categoria,
        card=cartao,
        date=date,
        due_date=due_date,
    )


def update_transaction(transaction_id, user, **kwargs):
    """Atualiza campos permitidos de uma transação existente.

    Valida ownership: levanta PermissionError se a transação não pertencer ao usuário
    ou não for encontrada. Revalida category_id e card_id se fornecidos.
    """
    try:
        transacao = Transaction.objects.get(id=transaction_id, is_active=True)
    except Transaction.DoesNotExist:
        raise PermissionError("Transação não encontrada.")

    if transacao.user != user:
        raise PermissionError("Sem permissão para editar esta transação.")

    # Valida campos antes de aplicar
    for campo, valor in kwargs.items():
        if campo not in CAMPOS_PERMITIDOS:
            continue

        if campo == "type" and valor not in TIPOS_VALIDOS:
            raise ValidationError(f"Tipo inválido. Escolha entre: {', '.join(TIPOS_VALIDOS)}.")

        if campo == "status" and valor not in STATUS_VALIDOS:
            raise ValidationError(f"Status inválido. Escolha entre: {', '.join(STATUS_VALIDOS)}.")

        if campo == "amount" and (valor is None or valor <= 0):
            raise ValidationError("O valor da transação deve ser maior que zero.")

        if campo == "category_id":
            categoria = _validar_categoria(valor, user)
            transacao.category = categoria
            continue

        if campo == "card_id":
            if valor is None:
                transacao.card = None
            else:
                cartao = _validar_cartao(valor, user)
                transacao.card = cartao
            continue

        setattr(transacao, campo, valor)

    transacao.save()
    return transacao


def deactivate_transaction(transaction_id, user):
    """Desativa (soft-delete) uma transação existente.

    Valida ownership: levanta PermissionError se a transação não pertencer ao usuário
    ou não for encontrada. Nunca realiza hard-delete.
    """
    try:
        transacao = Transaction.objects.get(id=transaction_id, is_active=True)
    except Transaction.DoesNotExist:
        raise PermissionError("Transação não encontrada.")

    if transacao.user != user:
        raise PermissionError("Sem permissão para desativar esta transação.")

    transacao.is_active = False
    transacao.save()
    return transacao


def update_status(transaction_id, user, status):
    """Atualiza o status de uma transação entre "pendente" e "pago".

    Valida que o status é válido e que a transação pertence ao usuário.
    Levanta ValidationError para status inválido e PermissionError para falhas de ownership.
    """
    if status not in STATUS_VALIDOS:
        raise ValidationError(f"Status inválido. Escolha entre: {', '.join(STATUS_VALIDOS)}.")

    try:
        transacao = Transaction.objects.get(id=transaction_id, is_active=True)
    except Transaction.DoesNotExist:
        raise PermissionError("Transação não encontrada.")

    if transacao.user != user:
        raise PermissionError("Sem permissão para alterar o status desta transação.")

    transacao.status = status
    transacao.save()
    return transacao
