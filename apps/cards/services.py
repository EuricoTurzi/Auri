from django.core.exceptions import ValidationError

from .models import Card

# Campos que podem ser atualizados via update_card
CAMPOS_PERMITIDOS = {
    "name",
    "brand",
    "last_four_digits",
    "card_type",
    "credit_limit",
    "billing_close_day",
    "billing_due_day",
}


def _validar_ultimos_quatro_digitos(last_four_digits):
    """Valida que os últimos 4 dígitos são exatamente 4 caracteres numéricos."""
    if not isinstance(last_four_digits, str) or len(last_four_digits) != 4 or not last_four_digits.isdigit():
        raise ValidationError("Os últimos 4 dígitos devem ser exatamente 4 caracteres numéricos.")


def create_card(
    user,
    name,
    brand,
    last_four_digits,
    card_type,
    credit_limit=None,
    billing_close_day=None,
    billing_due_day=None,
):
    """Cria um novo cartão para o usuário.

    Valida:
    - Últimos 4 dígitos: exatamente 4 chars numéricos.
    - Para cartão de crédito: credit_limit, billing_close_day e billing_due_day
      são opcionais, mas se fornecidos devem ser válidos.

    Levanta ValidationError para dados inválidos.
    """
    _validar_ultimos_quatro_digitos(last_four_digits)

    name = name.strip() if name else ""
    if not name:
        raise ValidationError("O nome do cartão não pode ser vazio.")

    brand = brand.strip() if brand else ""
    if not brand:
        raise ValidationError("A bandeira do cartão não pode ser vazia.")

    tipos_validos = {choice[0] for choice in Card.CARD_TYPE_CHOICES}
    if card_type not in tipos_validos:
        raise ValidationError(f"Tipo de cartão inválido. Escolha entre: {', '.join(tipos_validos)}.")

    return Card.objects.create(
        user=user,
        name=name,
        brand=brand,
        last_four_digits=last_four_digits,
        card_type=card_type,
        credit_limit=credit_limit,
        billing_close_day=billing_close_day,
        billing_due_day=billing_due_day,
    )


def update_card(card_id, user, **kwargs):
    """Atualiza campos permitidos de um cartão existente.

    Valida ownership: levanta PermissionError se o cartão não pertencer ao usuário
    ou não for encontrado. Revalida last_four_digits se fornecido.
    """
    try:
        card = Card.objects.get(id=card_id, is_active=True)
    except Card.DoesNotExist:
        raise PermissionError("Cartão não encontrado.")

    if card.user != user:
        raise PermissionError("Sem permissão para editar este cartão.")

    if "last_four_digits" in kwargs:
        _validar_ultimos_quatro_digitos(kwargs["last_four_digits"])

    for campo, valor in kwargs.items():
        if campo in CAMPOS_PERMITIDOS:
            setattr(card, campo, valor)

    card.save()
    return card


def deactivate_card(card_id, user):
    """Desativa (soft-delete) um cartão existente.

    Valida ownership: levanta PermissionError se o cartão não pertencer ao usuário
    ou não for encontrado.
    """
    try:
        card = Card.objects.get(id=card_id, is_active=True)
    except Card.DoesNotExist:
        raise PermissionError("Cartão não encontrado.")

    if card.user != user:
        raise PermissionError("Sem permissão para desativar este cartão.")

    card.is_active = False
    card.save()
    return card
