# Transactions

## Why

O controle de transações é o coração do Auri. Sem ele, o sistema não cumpre sua proposta de gerenciar finanças pessoais. O módulo precisa suportar registros manuais, recorrência automática e parcelamento — cobrindo os cenários reais de despesas e receitas do dia a dia.

## What

Usuário autenticado pode registrar transações de entrada (receita) e saída (despesa), com status de pagamento, categorização, vínculo opcional com cartão e data de vencimento. Transações podem ser marcadas como recorrentes (semanal/quinzenal/mensal) com geração automática de repetições, ou parceladas com divisão automática de valores. A exclusão de uma recorrência remove todas as repetições em cascata. Todas as operações possuem endpoints API correspondentes sob `/api/v1/transactions/` para integração mobile/SPA via JWT.

## Decisions

- Auth strategy (SSR): Session Auth — Django Templates.
- Auth strategy (API): JWT via `djangorestframework-simplejwt` — para mobile/SPA.
- API prefix: `/api/v1/transactions/`.
- Soft-delete: `is_active=False` como padrão para transações.
- Recorrência gera transações futuras automaticamente no momento da criação.
- CASCADE delete: exclusão de recorrência remove todas as repetições e o RecurringConfig.
- Parcelamento: sistema cria N registros de Installment automaticamente com valores divididos.
- Valores monetários: `DecimalField(max_digits=12, decimal_places=2)` para precisão financeira.
- Tenant isolation: todo queryset filtra por `request.user`.

> Assumption: Recorrência mensal em dia 31 — se o mês não possui dia 31, a transação é criada no último dia do mês. Razão: comportamento mais intuitivo para o usuário.

> Assumption: Parcelamento é exclusivo para transações de saída. Razão: parcelamento de receitas não é um cenário financeiro comum.

> Assumption: Ao criar recorrência, o sistema gera transações para os próximos 12 meses por padrão. Razão: horizonte razoável sem sobrecarregar o banco; pode ser ajustado futuramente.

## Constraints

### Must
- Todos os modelos herdam `BaseModel` (UUID pk, created_at, updated_at, is_active)
- Soft-delete via `is_active=False` — nunca usar hard DELETE em transações
- Tenant isolation: todo queryset deve filtrar por `request.user`
- Valores monetários com `DecimalField(max_digits=12, decimal_places=2)`
- Todas as views protegidas por `LoginRequiredMixin`
- Parcelamento deve gerar parcelas com numeração sequencial (1/N, 2/N...)
- Exclusão de recorrência deve remover TODAS as repetições futuras (CASCADE)

### Must Not
- Não permitir parcelamento em transações de entrada
- Não adicionar dependências externas sem listá-las aqui
- Não modificar arquivos fora do escopo de `apps/transactions/`, `templates/transactions/`, `tests/transactions/`
- Não permitir hard-delete de transações

### Out of Scope
- Importação de transações via arquivo (CSV/OFX)
- Notificações de vencimento (push/email)
- Conciliação bancária automática
- Integração direta com módulo Assistant (tratada na spec do Assistant)

## Data Model

```python
# BaseModel (abstract) — já existe em core/models.py
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

# Transaction — registro financeiro de entrada ou saída
class Transaction(BaseModel):
    TYPE_CHOICES = [("entrada", "Entrada"), ("saida", "Saída")]
    STATUS_CHOICES = [("pendente", "Pendente"), ("pago", "Pago")]

    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    card = models.ForeignKey(
        "cards.Card",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    is_installment = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Transação"
        verbose_name_plural = "Transações"

    def __str__(self):
        return f"{self.name} - R${self.amount}"


# RecurringConfig — configuração de recorrência vinculada a uma transação
class RecurringConfig(BaseModel):
    FREQUENCY_CHOICES = [
        ("semanal", "Semanal"),
        ("quinzenal", "Quinzenal"),
        ("mensal", "Mensal"),
    ]

    transaction = models.OneToOneField(
        "Transaction",
        on_delete=models.CASCADE,
        related_name="recurring_config",
    )
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)

    class Meta:
        verbose_name = "Configuração de Recorrência"
        verbose_name_plural = "Configurações de Recorrência"

    def __str__(self):
        return f"{self.transaction.name} - {self.frequency}"


# Installment — parcela individual de uma transação parcelada
class Installment(BaseModel):
    STATUS_CHOICES = [("pendente", "Pendente"), ("pago", "Pago")]

    parent_transaction = models.ForeignKey(
        "Transaction",
        on_delete=models.CASCADE,
        related_name="installments",
    )
    installment_number = models.IntegerField()
    total_installments = models.IntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    due_date = models.DateField()

    class Meta:
        ordering = ["installment_number"]
        verbose_name = "Parcela"
        verbose_name_plural = "Parcelas"

    def __str__(self):
        return f"{self.parent_transaction.name} - {self.installment_number}/{self.total_installments}"
```

## Current State

- App directory: `apps/transactions/` — existe, mas vazio (sem arquivos Python)
- Relevant existing files: nenhum arquivo no app ainda
- BaseModel: `core/models.py` — já implementado
- URL include: `core/urls.py` já possui `path('', include('apps.transactions.urls'))`
- Templates base: `templates/base.html`, `templates/includes/` existem
- Tests dir: `tests/__init__.py` existe
- Dependências: módulo Categories (FK) e Cards (FK) devem existir antes das migrations
- Patterns to follow: usar o padrão de service layer (ver `apps/accounts/services.py` quando implementado)

## Tasks

<!-- Layer order: Models → Migrations → Services → Selectors → Views/URLs → Templates → Admin → Tests -->

### T1: Models — Criar modelos Transaction, RecurringConfig e Installment
**What:** Criar os três modelos em `apps/transactions/models.py` conforme Data Model acima. Criar `apps/transactions/apps.py` com `TransactionsConfig` (name=`apps.transactions`). Criar `apps/transactions/__init__.py`.
**Files:** `apps/transactions/models.py`, `apps/transactions/apps.py`, `apps/transactions/__init__.py`
**Depends on:** none (mas Categories e Cards devem ter models criados para FK)
**Verify:** `python manage.py makemigrations transactions` gera a migration inicial sem erros

### T2: Migrations — Gerar e aplicar migration inicial
**What:** Gerar a migration inicial para o app transactions e aplicar ao banco. Garantir que as FKs para Category e Card resolvem corretamente.
**Files:** `apps/transactions/migrations/0001_initial.py`
**Depends on:** T1, Categories T2, Cards T2
**Verify:** `python manage.py migrate` executa sem erros; tabelas `transactions_transaction`, `transactions_recurringconfig` e `transactions_installment` existem no banco

### T3: Service — Criação de transação simples
**What:** Implementar funções de serviço para transações simples:
- `create_transaction(user, name, amount, type, category_id, date, description=None, card_id=None, due_date=None, status="pendente") -> Transaction` — cria transação validando que category e card (se informado) pertencem ao usuário.
- `update_transaction(transaction_id, user, **kwargs) -> Transaction` — atualiza campos. Valida ownership e integridade de FKs.
- `deactivate_transaction(transaction_id, user) -> Transaction` — soft-delete.
- `update_status(transaction_id, user, status) -> Transaction` — altera status (pendente ↔ pago).
**Files:** `apps/transactions/services.py`
**Depends on:** T2
**Verify:** Testes unitários chamam cada service com dados válidos e inválidos

### T4: Service — Recorrência
**What:** Implementar serviço de recorrência:
- `create_recurring_transaction(user, transaction_data, frequency) -> Transaction` — cria a transação principal com `is_recurring=True`, cria o `RecurringConfig`, e gera transações futuras (próximos 12 meses) com as datas calculadas conforme frequência (semanal: +7 dias, quinzenal: +14 dias, mensal: mesmo dia do próximo mês).
- `delete_recurring_transaction(transaction_id, user)` — remove a transação original, o RecurringConfig e todas as repetições futuras em cascata.
**Files:** `apps/transactions/services.py`
**Depends on:** T3
**Verify:** Ao criar recorrência mensal, N transações futuras são geradas com datas corretas; ao excluir, todas são removidas

### T5: Service — Parcelamento
**What:** Implementar serviço de parcelamento:
- `create_installment_transaction(user, transaction_data, total_installments) -> Transaction` — cria a transação principal com `is_installment=True` e `type="saida"`. Calcula `amount / total_installments` e cria N registros de `Installment` com numeração sequencial, valores divididos e due_dates mensais a partir da data da transação.
- Validação: parcelamento só é permitido para transações de saída.
**Files:** `apps/transactions/services.py`
**Depends on:** T3
**Verify:** Ao parcelar R$300 em 5x, 5 Installments são criados com R$60 cada e numeração 1/5 a 5/5

### T6: Selectors — Queries de leitura
**What:** Implementar selectors para consultas filtradas:
- `get_user_transactions(user, filters=None) -> QuerySet[Transaction]` — retorna transações ativas do usuário. Filtros opcionais: tipo, categoria, cartão, período (data início/fim), status.
- `get_transaction_by_id(transaction_id, user) -> Transaction` — retorna transação por ID, validando ownership.
- `get_installments(transaction_id, user) -> QuerySet[Installment]` — retorna parcelas de uma transação parcelada.
- `get_recurring_transactions(user) -> QuerySet[Transaction]` — retorna transações recorrentes ativas do usuário.
**Files:** `apps/transactions/selectors.py`
**Depends on:** T2
**Verify:** Selectors retornam apenas registros do usuário correto; filtros funcionam corretamente

### T7: Views + URLs — Endpoints de transações
**What:** Implementar views para CRUD de transações via Django Templates:
- `TransactionListView` (GET `/transactions/`) — lista transações ativas com filtros. Template: `templates/transactions/transaction_list.html`
- `TransactionCreateView` (GET/POST `/transactions/create/`) — formulário de criação com opções de recorrência e parcelamento. Template: `templates/transactions/transaction_form.html`. Redirect para list.
- `TransactionDetailView` (GET `/transactions/<uuid:pk>/`) — detalhe da transação com parcelas (se parcelada). Template: `templates/transactions/transaction_detail.html`
- `TransactionUpdateView` (GET/POST `/transactions/<uuid:pk>/edit/`) — edição. Template: `templates/transactions/transaction_form.html`. Redirect para list.
- `TransactionDeleteView` (POST `/transactions/<uuid:pk>/delete/`) — soft-delete ou CASCADE delete (se recorrente). Redirect para list.

Todas protegidas com `LoginRequiredMixin`. Configurar `apps/transactions/urls.py` com `app_name = "transactions"`.
**Files:** `apps/transactions/views.py`, `apps/transactions/urls.py`
**Depends on:** T3, T4, T5, T6
**Verify:** `GET /transactions/` retorna 200; `POST /transactions/create/` com dados válidos cria transação e redireciona

### T8: Templates — Páginas de transações
**What:** Criar templates para o módulo:
- `templates/transactions/transaction_list.html` — extends `base.html`. Lista com filtros (tipo, categoria, cartão, período, status). Exibe nome, valor, tipo (badge colorido), categoria, data, status. Botões de ação.
- `templates/transactions/transaction_form.html` — extends `base.html`. Formulário com campos dinâmicos: seção de recorrência (frequência) aparece condicionalmente quando `is_recurring` marcado; seção de parcelamento (quantidade de parcelas) aparece condicionalmente quando `is_installment` marcado.
- `templates/transactions/transaction_detail.html` — extends `base.html`. Exibe todos os dados da transação. Se parcelada, lista as parcelas com número, valor, status e vencimento.
**Files:** `templates/transactions/transaction_list.html`, `templates/transactions/transaction_form.html`, `templates/transactions/transaction_detail.html`
**Depends on:** T7
**Verify:** Páginas renderizam sem erros; formulário com recorrência e parcelamento funciona condicionalmente

### T9: Serializers — Serializers DRF para API
**What:** Criar serializers para a API:
- `TransactionSerializer` — campos: id, name, description, amount, type, status, category (id+name), card (id+name, nullable), date, due_date, is_recurring, is_installment, created_at. Read de FKs com nested serializer simplificado.
- `TransactionCreateSerializer` — campos: name, amount, type, category_id, card_id (opcional), date, due_date (opcional), description (opcional), status. Write-only.
- `RecurringTransactionCreateSerializer` — herda TransactionCreateSerializer + frequency.
- `InstallmentTransactionCreateSerializer` — herda TransactionCreateSerializer + total_installments.
- `InstallmentSerializer` — campos: id, installment_number, total_installments, amount, status, due_date.
- `TransactionFilterSerializer` — campos: type, category_id, card_id, date_start, date_end, status. Para validação de query params.
**Files:** `apps/transactions/serializers.py`
**Depends on:** T3, T4, T5
**Verify:** Serializers validam dados corretamente; nested read funciona; write serializers criam via services

### T10: API Views + URLs — Endpoints REST
**What:** Implementar API views com DRF:
- `TransactionListCreateAPIView` (GET/POST `/api/v1/transactions/`) — lista transações com filtros via query params; cria transação simples. Requer JWT.
- `TransactionDetailAPIView` (GET/PUT/DELETE `/api/v1/transactions/<uuid:pk>/`) — detalhe, atualização e soft-delete. Requer JWT.
- `RecurringTransactionCreateAPIView` (POST `/api/v1/transactions/recurring/`) — cria transação recorrente. Requer JWT.
- `RecurringTransactionDeleteAPIView` (DELETE `/api/v1/transactions/recurring/<uuid:pk>/`) — exclui recorrência em cascata. Requer JWT.
- `InstallmentTransactionCreateAPIView` (POST `/api/v1/transactions/installment/`) — cria transação parcelada. Requer JWT.
- `InstallmentListAPIView` (GET `/api/v1/transactions/<uuid:pk>/installments/`) — lista parcelas de uma transação. Requer JWT.
- `TransactionStatusUpdateAPIView` (PATCH `/api/v1/transactions/<uuid:pk>/status/`) — atualiza status (pendente ↔ pago). Requer JWT.

Todas com `permission_classes = [IsAuthenticated]`. Configurar `apps/transactions/api_urls.py`. Incluir em `core/urls.py`: `path('api/v1/transactions/', include('apps.transactions.api_urls'))`.
**Files:** `apps/transactions/api_views.py`, `apps/transactions/api_urls.py`, `core/urls.py`
**Depends on:** T9
**Verify:** `GET /api/v1/transactions/` com JWT retorna lista; `POST` cria transação; endpoints de recorrência e parcelamento funcionam; sem JWT retorna 401

### T11: Admin — Registro no Django Admin
**What:** Registrar modelos no Django Admin:
- `TransactionAdmin`: list_display (name, user, amount, type, status, category, date), list_filter (type, status, is_recurring, is_installment), search_fields (name, user__email)
- `RecurringConfigAdmin`: list_display (transaction, frequency, created_at)
- `InstallmentAdmin`: list_display (parent_transaction, installment_number, total_installments, amount, status, due_date), list_filter (status)
**Files:** `apps/transactions/admin.py`
**Depends on:** T2
**Verify:** `/admin/transactions/` lista registros; formulários funcionam end-to-end

### T12: Tests — Testes unitários e de integração
**What:** Implementar testes cobrindo:
- **Services:** criar transação simples, criar recorrência (verificar N transações geradas), criar parcelamento (verificar divisão de valores e numeração), delete cascade de recorrência, validação de parcelamento apenas para saída, validação de ownership em category/card
- **Selectors:** listar transações por usuário, filtros (tipo, categoria, período, status, cartão), get_installments, tenant isolation
- **Views (SSR):** acesso autenticado vs não autenticado, CRUD completo via POST, criação com recorrência, criação com parcelamento
- **API:** GET list com JWT e filtros, POST create, PUT update, DELETE soft-delete, POST recurring, DELETE recurring cascade, POST installment, GET installments, PATCH status, sem JWT → 401, tenant isolation via API
**Files:** `tests/transactions/__init__.py`, `tests/transactions/test_services.py`, `tests/transactions/test_views.py`, `tests/transactions/test_api.py`
**Depends on:** T7, T8, T10, T11
**Verify:** `pytest tests/transactions/` passa com 0 falhas

## Validation

**Happy path:**
1. Usuário acessa `/transactions/` — lista vazia
2. Usuário cria transação de saída: "Mercado", R$150, categoria "Alimentação", cartão "Nubank", data hoje → transação aparece na lista com status "pendente"
3. Usuário altera status para "pago" → badge atualiza
4. Usuário cria transação recorrente mensal: "Aluguel", R$1.500, categoria "Moradia" → 12 transações futuras são geradas
5. Usuário cria transação parcelada: "Notebook", R$6.000, 10x, cartão "Itaú" → 10 parcelas de R$600 criadas (1/10 a 10/10)
6. Usuário visualiza detalhe da transação parcelada → lista de parcelas com status individual
7. Usuário exclui transação recorrente → todas as repetições futuras são removidas

**Edge cases:**
- Usuário tenta parcelar transação de entrada → erro de validação
- Usuário tenta vincular cartão de outro usuário → erro de validação
- Usuário tenta vincular categoria de outro usuário → erro de validação
- Recorrência mensal dia 31 em mês com 30 dias → transação no dia 30
- Parcelamento com valor que não divide exatamente (ex: R$100 em 3x) → centavos distribuídos nas primeiras parcelas
- Usuário não autenticado → redirect para login

**Commands:**
```bash
pytest tests/transactions/
# Manual: criar transação com recorrência e verificar geração de futuras
# Manual: criar parcelamento e verificar divisão de valores no detalhe
# Manual: excluir recorrência e confirmar CASCADE
```
