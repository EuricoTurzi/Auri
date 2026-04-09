"""
Serviços do módulo assistant.

Responsabilidades:
- Transcrição de áudio via OpenAI Whisper API
- Interpretação de texto via OpenAI GPT para extração de transações
- Criação, confirmação e cancelamento de interações do assistente
"""

import json
import openai
from django.apps import apps
from django.conf import settings


class ServiceError(Exception):
    """Exceção base para erros de serviço do módulo assistant."""
    pass


def transcribe_audio(audio_file) -> str:
    """
    Recebe um arquivo de áudio (UploadedFile do Django), envia para a API
    OpenAI Whisper e retorna o texto transcrito.

    Args:
        audio_file: Objeto de arquivo compatível com o SDK OpenAI (UploadedFile,
                    arquivo aberto em modo binário ou tupla (nome, bytes, mime-type)).

    Returns:
        str: Texto transcrito pelo modelo Whisper.

    Raises:
        ServiceError: Quando a API do OpenAI retorna erro ou a chave está ausente.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ServiceError(
            "OPENAI_API_KEY não configurada. Defina a variável de ambiente no arquivo .env."
        )

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.name, audio_file.read(), audio_file.content_type or "audio/webm"),
        )
        return response.text
    except openai.AuthenticationError as exc:
        raise ServiceError(f"Chave de API inválida ou expirada: {exc}") from exc
    except openai.RateLimitError as exc:
        raise ServiceError(f"Limite de requisições atingido na API OpenAI: {exc}") from exc
    except openai.APIConnectionError as exc:
        raise ServiceError(f"Falha de conexão com a API OpenAI: {exc}") from exc
    except openai.OpenAIError as exc:
        raise ServiceError(f"Erro inesperado ao chamar a API OpenAI Whisper: {exc}") from exc


def build_system_prompt(user) -> str:
    """
    Monta o prompt do sistema para o GPT com as categorias e cartões ativos do usuário.

    O prompt instrui o modelo a extrair campos de uma transação financeira a partir
    de texto em linguagem natural, retornando um JSON estruturado com:
    - Campos obrigatórios: name, amount, type, date
    - Campos opcionais (nunca solicitar): description, card
    - Categoria: inferida semanticamente; se não houver match, retorna suggested_category_name
    - assistant_message: resposta humanizada em pt-br para o usuário

    Args:
        user: Instância do usuário autenticado (CustomUser).

    Returns:
        str: Prompt de sistema formatado para envio ao GPT.
    """
    from datetime import date as _date
    Category = apps.get_model("categories", "Category")
    Card = apps.get_model("cards", "Card")

    categorias = Category.objects.filter(user=user, is_active=True).values("id", "name")
    cartoes = Card.objects.filter(user=user, is_active=True).values("id", "name")

    lista_categorias = "\n".join(
        f"  - id: {str(c['id'])}, nome: {c['name']}" for c in categorias
    ) or "  (nenhuma categoria cadastrada)"

    lista_cartoes = "\n".join(
        f"  - id: {str(c['id'])}, nome: {c['name']}" for c in cartoes
    ) or "  (nenhum cartão cadastrado)"

    hoje = _date.today().strftime("%Y-%m-%d")

    return f"""Você é Auri, um assistente financeiro pessoal simpático e descomplicado.
Seu objetivo é ajudar o usuário a registrar transações financeiras de forma natural e sem complicação.
Hoje é {hoje}.

## Categorias do usuário:
{lista_categorias}

## Cartões do usuário:
{lista_cartoes}

## Sua tarefa
Extraia os dados da transação a partir do que o usuário disse, em linguagem natural.

### Campos OBRIGATÓRIOS (pergunte ao usuário se não estiverem claros):
- **name**: nome curto da transação (ex: "Supermercado", "Salário", "Netflix")
- **amount**: valor numérico. Apenas números, sem símbolo de moeda (ex: 45.90)
- **type**: "entrada" (dinheiro entrando: salário, pix recebido, etc.) ou "saida" (dinheiro saindo: compra, conta, etc.)
- **date**: data no formato "YYYY-MM-DD". "hoje" = {hoje}. Se não informada, use null.

### Campos OPCIONAIS (NUNCA peça ao usuário, tente inferir):
- **description**: contexto extra mencionado. null se não houver.
- **card**: objeto {{"id": "...", "name": "..."}} APENAS se o usuário mencionar explicitamente um cartão pelo nome. Senão, null. Use SOMENTE cartões da lista acima.
- **category**: tente inferir semanticamente a partir das categorias do usuário:
  - Exemplos: "supermercado" ou "mercado" → busque categoria "Alimentação"; "netflix" ou "spotify" → "Streaming" ou "Entretenimento"; "gasolina" ou "uber" → "Transporte"
  - Se encontrar categoria compatível na lista: retorne {{"id": "...", "name": "..."}}
  - Se NÃO encontrar nenhuma categoria compatível: retorne category: null e suggested_category_name com uma sugestão sensata.
  - Se o usuário não tiver categorias: retorne category: null e uma suggested_category_name
- **is_recurring**: true se o usuário mencionar algo recorrente (ex: "todo mês", "toda semana", "mensalidade", "fixo"). false ou null caso contrário.
- **frequency**: se is_recurring for true, infira a frequência: "semanal", "quinzenal" ou "mensal". null caso contrário.
- **is_installment**: true se o usuário mencionar parcelas (ex: "3x", "em 5 vezes", "parcelei em 12x"). false ou null caso contrário. Apenas para saídas (type="saida").
- **total_installments**: número inteiro de parcelas se is_installment for true (mínimo 2). null caso contrário.

### Campo de mensagem:
- **assistant_message**: resposta curta, amigável e natural em português para o usuário.
  - Se tiver todos os dados obrigatórios: confirme o que entendeu de forma descontraída. Ex: "Ótimo! Vou registrar uma saída de R$ 50,00 no supermercado."
  - Se faltar algum dado obrigatório: pergunte de forma natural e gentil. Ex: "Quanto você gastou?" / "Foi uma entrada ou uma saída?"
  - NUNCA use linguagem técnica. NUNCA mencione nomes de campos em inglês.

## Regras
1. NUNCA invente dados. Extraia apenas o que está no texto.
2. Campos opcionais (description, card): null se não mencionados. NUNCA pergunte sobre eles.
3. missing_fields: liste APENAS campos obrigatórios ausentes (name, amount, type, date). NUNCA inclua category, description ou card.
4. Para cartões: use SOMENTE os da lista. Se não mencionado explicitamente, null.
5. Responda APENAS com JSON, sem texto extra, sem markdown.
6. Parcelamento (is_installment) apenas para transações de saída (type="saida").
7. Recorrência e parcelamento são mutuamente exclusivos — uma transação não pode ser ambos.

## Formato de resposta (JSON)
{{
  "name": "string ou null",
  "amount": número ou null,
  "type": "entrada" | "saida" | null,
  "category": {{"id": "uuid", "name": "string"}} | null,
  "suggested_category_name": "string ou null",
  "date": "YYYY-MM-DD" | null,
  "description": "string ou null",
  "card": {{"id": "uuid", "name": "string"}} | null,
  "is_recurring": true | false | null,
  "frequency": "semanal" | "quinzenal" | "mensal" | null,
  "is_installment": true | false | null,
  "total_installments": número inteiro ou null,
  "missing_fields": ["campos OBRIGATÓRIOS ausentes — nunca category/description/card"],
  "assistant_message": "mensagem amigável para o usuário"
}}"""


def interpret_transaction(user, text: str) -> dict:
    """
    Envia um texto em linguagem natural para o GPT e extrai os dados de uma transação financeira.

    Utiliza o prompt do sistema construído por `build_system_prompt` para instruir o modelo
    a retornar um JSON estruturado com os campos da transação. Campos não identificados
    são retornados como null e listados em missing_fields.

    Args:
        user: Instância do usuário autenticado (CustomUser).
        text (str): Texto em linguagem natural descrevendo a transação.

    Returns:
        dict: Dicionário com os campos extraídos da transação:
            - name (str | None)
            - amount (float | None)
            - type ("entrada" | "saida" | None)
            - category ({"id": str, "name": str} | None)
            - suggested_category_name (str | None)
            - date ("YYYY-MM-DD" | None)
            - description (str | None)
            - card ({"id": str, "name": str} | None)
            - missing_fields (list[str])
            - assistant_message (str)

    Raises:
        ServiceError: Quando a API do OpenAI retorna erro, a chave está ausente
                      ou o JSON retornado é inválido.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ServiceError(
            "OPENAI_API_KEY não configurada. Defina a variável de ambiente no arquivo .env."
        )

    system_prompt = build_system_prompt(user)

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        raw_content = response.choices[0].message.content
    except openai.AuthenticationError as exc:
        raise ServiceError(f"Chave de API inválida ou expirada: {exc}") from exc
    except openai.RateLimitError as exc:
        raise ServiceError(f"Limite de requisições atingido na API OpenAI: {exc}") from exc
    except openai.APIConnectionError as exc:
        raise ServiceError(f"Falha de conexão com a API OpenAI: {exc}") from exc
    except openai.OpenAIError as exc:
        raise ServiceError(f"Erro inesperado ao chamar a API OpenAI GPT: {exc}") from exc

    try:
        data = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ServiceError(
            f"Resposta do GPT não é um JSON válido: {exc}\nConteúdo recebido: {raw_content!r}"
        ) from exc

    # Garantir que missing_fields sempre seja uma lista
    if "missing_fields" not in data or not isinstance(data.get("missing_fields"), list):
        data["missing_fields"] = []

    return data


# ---------------------------------------------------------------------------
# Gerenciamento de interações
# ---------------------------------------------------------------------------


def create_interaction(user, input_type, input_content, llm_response):
    """
    Cria e retorna uma AssistantInteraction com status "pendente".

    Args:
        user: Instância do usuário autenticado (CustomUser).
        input_type (str): Tipo de entrada — "texto" ou "audio".
        input_content (str): Texto digitado pelo usuário ou transcrição do áudio.
        llm_response (dict): Dados extraídos pela LLM.

    Returns:
        AssistantInteraction: Interação criada com status "pendente".
    """
    AssistantInteraction = apps.get_model("assistant", "AssistantInteraction")
    return AssistantInteraction.objects.create(
        user=user,
        input_type=input_type,
        input_content=input_content,
        llm_response=llm_response,
        status="pendente",
    )


def confirm_interaction(interaction_id, user, adjusted_data=None):
    """
    Confirma uma interação pendente, criando a transação correspondente.

    Busca a AssistantInteraction pelo interaction_id e verifica que pertence ao
    usuário (isolamento de tenant). Se adjusted_data for fornecido, usa esses
    dados para criar a transação; caso contrário, usa interaction.llm_response.
    Atualiza o status da interação para "confirmado" e vincula a transação criada.

    Args:
        interaction_id: UUID da interação a ser confirmada.
        user: Instância do usuário autenticado (CustomUser).
        adjusted_data (dict | None): Dados ajustados pelo usuário. Se None,
            usa os dados retornados pela LLM.

    Returns:
        Transaction: Transação criada.

    Raises:
        ServiceError: Se a interação não for encontrada, não pertencer ao usuário
                      ou não estiver com status "pendente".
    """
    from apps.transactions.services import (
        create_transaction,
        create_recurring_transaction,
        create_installment_transaction,
    )

    AssistantInteraction = apps.get_model("assistant", "AssistantInteraction")

    try:
        interaction = AssistantInteraction.objects.get(id=interaction_id)
    except AssistantInteraction.DoesNotExist:
        raise ServiceError("Interação não encontrada.")

    if interaction.user != user:
        raise ServiceError("Sem permissão para confirmar esta interação.")

    if interaction.status != "pendente":
        raise ServiceError(
            f"Não é possível confirmar uma interação com status '{interaction.status}'."
        )

    dados = adjusted_data if adjusted_data is not None else interaction.llm_response

    # Extrai category_id e card_id dos objetos aninhados, se presentes
    category = dados.get("category")
    card = dados.get("card")
    category_id = category.get("id") if isinstance(category, dict) else category
    card_id = card.get("id") if isinstance(card, dict) else card

    transaction_data = {
        "name": dados.get("name"),
        "amount": dados.get("amount"),
        "type": dados.get("type"),
        "category_id": category_id,
        "date": dados.get("date"),
        "description": dados.get("description"),
        "card_id": card_id,
    }

    is_recurring = dados.get("is_recurring", False)
    frequency = dados.get("frequency")
    is_installment = dados.get("is_installment", False)
    total_installments = dados.get("total_installments")

    if is_recurring and frequency:
        transaction = create_recurring_transaction(
            user=user,
            transaction_data=transaction_data,
            frequency=frequency,
        )
    elif is_installment and total_installments:
        transaction = create_installment_transaction(
            user=user,
            transaction_data=transaction_data,
            total_installments=int(total_installments),
        )
    else:
        transaction = create_transaction(user=user, **transaction_data)

    interaction.status = "confirmado"
    interaction.transaction = transaction
    interaction.save()

    return transaction


def cancel_interaction(interaction_id, user):
    """
    Cancela uma interação do assistente.

    Busca a AssistantInteraction pelo interaction_id e verifica que pertence ao
    usuário (isolamento de tenant). Marca o status como "cancelado" e salva.

    Args:
        interaction_id: UUID da interação a ser cancelada.
        user: Instância do usuário autenticado (CustomUser).

    Returns:
        AssistantInteraction: Interação atualizada com status "cancelado".

    Raises:
        ServiceError: Se a interação não for encontrada ou não pertencer ao usuário.
    """
    AssistantInteraction = apps.get_model("assistant", "AssistantInteraction")

    try:
        interaction = AssistantInteraction.objects.get(id=interaction_id)
    except AssistantInteraction.DoesNotExist:
        raise ServiceError("Interação não encontrada.")

    if interaction.user != user:
        raise ServiceError("Sem permissão para cancelar esta interação.")

    interaction.status = "cancelado"
    interaction.save()

    return interaction
