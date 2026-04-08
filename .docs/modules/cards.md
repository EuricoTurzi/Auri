# Cards

## Entrega Esperada

O módulo `Cards` é responsável pelo cadastro e gerenciamento de cartões do usuário dentro da plataforma. Funciona como uma "carteira digital", permitindo que o usuário organize seus gastos por cartão e acompanhe limite disponível e datas de fatura.
Cartões podem ser de crédito ou débito — o próprio usuário define o tipo ao cadastrar.

## Regras de Negócio

`Cada cartão pertence exclusivamente ao usuário autenticado.`

- O usuário pode cadastrar múltiplos cartões.

- Campos obrigatórios: nome do cartão, bandeira, últimos 4 dígitos, tipo (crédito/débito).
    - Campos opcionais (crédito): limite total, dia de fechamento da fatura, dia de vencimento da fatura.

- O **tipo do cartão** é definido pelo usuário no momento do cadastro:
    - `crédito`: possui controle de limite e fatura.
    - `débito`: sem controle de limite/fatura, funciona apenas como agrupador de transações.

### Controle de Limite (Crédito)

- O usuário cadastra o **limite total** do cartão.
- O **limite disponível** é calculado automaticamente: `limite_total - soma das transações vinculadas ao cartão no período da fatura`.
- O sistema deve exibir o limite disponível em tempo real na interface.

### Fatura

- O **dia de fechamento** determina o corte mensal da fatura.
- O **dia de vencimento** determina a data de pagamento da fatura.
- Transações vinculadas ao cartão são agrupadas por período de fatura com base no dia de fechamento.

- Soft-delete é o padrão. Ao desativar um cartão, as transações vinculadas permanecem no histórico.

`Para auditoria, todo cartão deve herdar o BaseModel contido em core/models.py`

## Modelo de Dados

- Card (Herda de BaseModel):
    - user: ForeignKey → CustomUser
    - name: CharField
    - brand: CharField (ex: Visa, Mastercard, Elo)
    - last_four_digits: CharField (max_length=4)
    - card_type: CharField (choices: crédito, débito)
    - credit_limit: DecimalField (null=True, blank=True)
    - billing_close_day: IntegerField (null=True, blank=True)
    - billing_due_day: IntegerField (null=True, blank=True)

## Fluxo de Cadastro de Cartão

- Usuário preenche o formulário com os dados do cartão.
- Serializer valida os campos obrigatórios e regras específicas por tipo:
    - Se crédito: limite, dia de fechamento e dia de vencimento são recomendados.
    - Se débito: campos de limite e fatura são ignorados.
- Serializer valida que os últimos 4 dígitos contêm exatamente 4 caracteres numéricos.
- Service cria o cartão vinculado ao usuário autenticado.
- Retorna resposta de sucesso com os dados do cartão criado.

## Fluxo de Consulta de Limite

- Usuário acessa a visualização do cartão de crédito.
- Service calcula o limite disponível em tempo real:
    - Soma todas as transações de saída vinculadas ao cartão no período da fatura atual.
    - Subtrai do limite total cadastrado.
- Retorna o cartão com limite total e limite disponível.
