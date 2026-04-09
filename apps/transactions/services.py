import calendar
from datetime import timedelta
from decimal import Decimal, ROUND_DOWN

from django.apps import apps as django_apps
from django.core.exceptions import ValidationError

from .models import Installment, RecurringConfig, Transaction

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

    # Limite exato: mesma data 12 meses no futuro (usando lógica mensal)
    data_limite = _proxima_data(data_base, "mensal", 12)

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
            recurring_parent=transacao_pai,
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

    # Soft-delete em todas as ocorrências filhas vinculadas via recurring_parent
    Transaction.objects.filter(
        recurring_parent=transacao,
        is_active=True,
    ).update(is_active=False)


# ---------------------------------------------------------------------------
# Parcelamento
# ---------------------------------------------------------------------------


def create_installment_transaction(user, transaction_data, total_installments):
    """Cria uma transação parcelada com suas parcelas individuais.

    Parâmetros:
        user                — usuário autenticado
        transaction_data    — dict com: name, amount, type, category_id, date,
                              description (opt), card_id (opt), due_date (opt),
                              status (opt, padrão "pendente")
        total_installments  — número total de parcelas (mínimo 2)

    Regras:
        - Apenas transações do tipo "saida" podem ser parceladas.
        - O número mínimo de parcelas é 2.
        - O valor deve ser maior que zero.
        - O valor de cada parcela é calculado com distribuição de centavos:
          o remainder é distribuído (1 centavo) nas primeiras parcelas.
        - A data de vencimento de cada parcela é calculada adicionando N meses
          à data da transação pai, respeitando o limite de dias do mês.

    Retorna a transação pai com is_installment=True.
    Levanta ValidationError para dados inválidos.
    """
    # Valida tipo
    if transaction_data.get("type") != "saida":
        raise ValidationError("Parcelamento é permitido apenas para transações de saída.")

    # Valida total de parcelas
    if not isinstance(total_installments, int) or total_installments < 2:
        raise ValidationError("O número de parcelas deve ser no mínimo 2.")

    # Valida amount antecipadamente (necessário para o cálculo antes de create_transaction)
    amount = transaction_data.get("amount")
    if amount is None or amount <= 0:
        raise ValidationError("O valor da transação deve ser maior que zero.")

    # Cria a transação pai via service existente
    transacao_pai = create_transaction(user=user, **transaction_data)

    # Marca como parcelada e salva
    transacao_pai.is_installment = True
    transacao_pai.save()

    # Cálculo preciso do valor de cada parcela com distribuição de centavos
    amount_decimal = Decimal(str(transacao_pai.amount))
    total = Decimal(str(total_installments))

    unit = (amount_decimal / total).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    remainder = amount_decimal - (unit * total)
    # quantidade de parcelas que recebem 1 centavo a mais
    extra_count = int(remainder / Decimal("0.01"))

    # Cria cada parcela
    data_base = transacao_pai.date

    for i in range(1, total_installments + 1):
        # Distribui o centavo restante nas primeiras parcelas
        parcela_amount = unit + Decimal("0.01") if i <= extra_count else unit

        # Calcula due_date: data_base + i meses usando o helper existente
        due_date = _proxima_data(data_base, "mensal", i)

        Installment.objects.create(
            parent_transaction=transacao_pai,
            installment_number=i,
            total_installments=total_installments,
            amount=parcela_amount,
            due_date=due_date,
        )

    return transacao_pai
