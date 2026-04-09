import calendar
from datetime import timedelta

from django.apps import apps as django_apps
from django.core.exceptions import ValidationError

from .models import RecurringConfig, Transaction

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


# ---------------------------------------------------------------------------
# Recorrência
# ---------------------------------------------------------------------------

FREQUENCIAS_VALIDAS = {"semanal", "quinzenal", "mensal"}


def _proxima_data(data_base, frequencia, iteracao):
    """Calcula a próxima data de ocorrência conforme a frequência.

    - semanal:   +7 dias por iteração
    - quinzenal: +14 dias por iteração
    - mensal:    mesmo dia no mês seguinte, respeitando o limite de dias do mês
    """
    if frequencia == "semanal":
        return data_base + timedelta(weeks=iteracao)
    if frequencia == "quinzenal":
        return data_base + timedelta(days=14 * iteracao)

    # mensal — avança mês a mês a partir da data original
    mes = data_base.month + iteracao
    ano = data_base.year + (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia)
    return data_base.replace(year=ano, month=mes, day=dia)


def create_recurring_transaction(user, transaction_data, frequency):
    """Cria uma transação recorrente com suas ocorrências futuras (12 meses).

    Parâmetros:
        user            — usuário autenticado
        transaction_data — dict com: name, amount, type, category_id, date,
                           description (opt), card_id (opt), due_date (opt),
                           status (opt, padrão "pendente")
        frequency       — "semanal", "quinzenal" ou "mensal"

    Retorna a transação pai (original).
    Levanta ValidationError para frequência inválida.
    """
    if frequency not in FREQUENCIAS_VALIDAS:
        raise ValidationError(
            f"Frequência inválida. Escolha entre: {', '.join(sorted(FREQUENCIAS_VALIDAS))}."
        )

    # Cria a transação pai usando a função existente (sem is_recurring ainda)
    transacao_pai = create_transaction(user=user, **transaction_data)

    # Marca como recorrente e salva
    transacao_pai.is_recurring = True
    transacao_pai.save()

    # Cria a configuração de recorrência
    RecurringConfig.objects.create(transaction=transacao_pai, frequency=frequency)

    # Gera ocorrências futuras para os próximos 12 meses
    data_base = transacao_pai.date
    from datetime import date as date_type

    if hasattr(data_base, "date"):
        # Garante que seja um objeto date puro, não datetime
        data_base = data_base.date() if hasattr(data_base, "date") and callable(data_base.date) else data_base

    # Limite: 12 meses a partir da data original
    mes_limite = data_base.month + 12
    ano_limite = data_base.year + (mes_limite - 1) // 12
    mes_limite = (mes_limite - 1) % 12 + 1
    ultimo_dia_limite = calendar.monthrange(ano_limite, mes_limite)[1]
    from datetime import date as dt_date
    data_limite = dt_date(ano_limite, mes_limite, ultimo_dia_limite)

    iteracao = 1
    while True:
        proxima = _proxima_data(data_base, frequency, iteracao)
        if proxima > data_limite:
            break

        Transaction.objects.create(
            user=user,
            name=transacao_pai.name,
            description=transacao_pai.description,
            amount=transacao_pai.amount,
            type=transacao_pai.type,
            status=transacao_pai.status,
            category=transacao_pai.category,
            card=transacao_pai.card,
            date=proxima,
            due_date=None,
            is_recurring=True,
        )
        iteracao += 1

    return transacao_pai


def delete_recurring_transaction(transaction_id, user):
    """Exclui uma transação recorrente e suas ocorrências futuras.

    - Valida ownership da transação pai.
    - Valida que a transação é de fato recorrente (tem RecurringConfig).
    - Hard-delete no RecurringConfig.
    - Soft-delete (is_active=False) na transação pai e em todas as ocorrências
      futuras com as mesmas características (nome, valor, categoria).

    Levanta PermissionError para falhas de ownership/não encontrado.
    Levanta ValidationError se a transação não for recorrente.
    """
    try:
        transacao = Transaction.objects.get(id=transaction_id, is_active=True)
    except Transaction.DoesNotExist:
        raise PermissionError("Transação não encontrada.")

    if transacao.user != user:
        raise PermissionError("Sem permissão para excluir esta transação.")

    # Valida que é uma transação recorrente
    try:
        config = transacao.recurring_config
    except RecurringConfig.DoesNotExist:
        raise ValidationError("Esta transação não possui configuração de recorrência.")

    # Hard-delete na configuração de recorrência
    config.delete()

    # Soft-delete na transação pai
    transacao.is_active = False
    transacao.save()

    # Soft-delete em todas as ocorrências futuras com as mesmas características
    Transaction.objects.filter(
        user=user,
        is_recurring=True,
        is_active=True,
        name=transacao.name,
        amount=transacao.amount,
        category=transacao.category,
        date__gte=transacao.date,
    ).update(is_active=False)
