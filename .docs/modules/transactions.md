# Transactions

## Entrega Esperada

O módulo `Transactions` é o coração do sistema. Responsável pelo registro, controle e visualização de todas as movimentações financeiras do usuário — tanto entradas quanto saídas.
O módulo contempla funcionalidades de recorrência automática e parcelamento, eliminando o trabalho manual de registros repetitivos.

## Regras de Negócio

`Toda transação pertence exclusivamente ao usuário autenticado.`

- Transações possuem dois tipos: **entrada** (receita) e **saída** (despesa).

- Campos obrigatórios: nome, valor, tipo (entrada/saída), categoria e data.
    - Campos opcionais: descrição, data de vencimento, cartão vinculado.

- Toda transação possui um **status** que indica sua situação atual:
    - `pendente`: transação registrada mas ainda não efetivada.
    - `pago`: transação efetivada/confirmada.

- Transações de saída podem ser vinculadas a um **cartão** cadastrado pelo usuário no módulo Cards.

### Recorrência

- O usuário pode marcar uma transação como **recorrente**.
- A frequência de repetição pode ser: **semanal**, **quinzenal** ou **mensal**.
- A repetição ocorre sempre no mesmo dia da semana (semanal/quinzenal) ou do mês (mensal).
- Ao excluir uma transação recorrente, **todas as repetições futuras são removidas em cascata** (CASCADE).
- O sistema gera automaticamente as transações futuras com base na frequência selecionada.

### Parcelamento

- O parcelamento é opcional e exclusivo para transações de saída.
- O usuário informa o **valor total** e a **quantidade de parcelas**.
- O sistema divide o valor total pela quantidade de parcelas e cria N transações automaticamente.
    - Exemplo: R$ 300,00 em 5x → 5 transações de R$ 60,00 cada.
- Cada parcela gerada contém o **número da parcela** (ex: 1/5, 2/5, 3/5...).
- As parcelas são transações independentes, permitindo controle individual de status.

`Para auditoria, toda transação deve herdar o BaseModel contido em core/models.py`

## Modelo de Dados

- Transaction (Herda de BaseModel):
    - user: ForeignKey → CustomUser
    - name: CharField
    - description: TextField (null=True, blank=True)
    - amount: DecimalField
    - type: CharField (choices: entrada, saída)
    - status: CharField (choices: pendente, pago)
    - category: ForeignKey → Category
    - card: ForeignKey → Card (null=True, blank=True)
    - due_date: DateField (null=True, blank=True)
    - date: DateField
    - is_recurring: BooleanField (default=False)
    - is_installment: BooleanField (default=False)

- RecurringConfig (Herda de BaseModel):
    - transaction: OneToOneField → Transaction
    - frequency: CharField (choices: semanal, quinzenal, mensal)

- Installment (Herda de BaseModel):
    - parent_transaction: ForeignKey → Transaction
    - installment_number: IntegerField
    - total_installments: IntegerField
    - amount: DecimalField
    - status: CharField (choices: pendente, pago)
    - due_date: DateField

## Fluxo de Criação de Transação

- Usuário preenche o formulário com os dados da transação.
- Serializer valida os campos obrigatórios, tipo, categoria e cartão (se informado).
- Service cria a transação principal.
- Se marcada como recorrente, o Service cria o RecurringConfig e gera as transações futuras conforme a frequência.
- Se marcada como parcelamento, o Service calcula o valor por parcela e cria os registros de Installment automaticamente.
- Retorna resposta de sucesso com os dados da transação criada.

## Fluxo de Exclusão de Recorrência

- Usuário solicita exclusão de uma transação recorrente.
- Service identifica todas as repetições futuras vinculadas.
- Todas as transações futuras e o RecurringConfig são removidos em cascata.
- Retorna confirmação de exclusão.
