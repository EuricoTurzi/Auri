# Cards

## Why

O usuário precisa organizar seus gastos por meio de pagamento. O módulo Cards funciona como uma "carteira digital" onde o usuário cadastra seus cartões de crédito e débito, permitindo vincular transações a cartões específicos, controlar limites de crédito em tempo real e acompanhar faturas por período de fechamento.

## What

Usuário autenticado pode cadastrar, editar, listar e desativar cartões. Cartões de crédito possuem controle de limite (cadastrado pelo usuário) com cálculo automático de limite disponível, dia de fechamento e dia de vencimento da fatura. Cartões de débito funcionam como agrupadores de transações sem controle de limite/fatura. Transações de saída podem ser vinculadas a um cartão. Todas as operações possuem endpoints API correspondentes sob `/api/v1/cards/` para integração mobile/SPA via JWT.

## Decisions

- Auth strategy (SSR): Session Auth — Django Templates.
- Auth strategy (API): JWT via `djangorestframework-simplejwt` — para mobile/SPA.
- API prefix: `/api/v1/cards/`.
- Soft-delete: `is_active=False` como padrão. Cartão desativado mantém histórico de transações.
- Limite disponível calculado em tempo real (não armazenado em banco).
- Período de fatura derivado do `billing_close_day`.
- Tenant isolation: todo queryset filtra por `request.user`.
- Últimos 4 dígitos: validação de exatamente 4 caracteres numéricos.

> Assumption: Bandeiras serão CharField livre, sem choices fixos. Razão: flexibilidade para bandeiras regionais/novas sem necessidade de migration.

> Assumption: Período de fatura — transações com data entre `billing_close_day` do mês anterior +1 até `billing_close_day` do mês atual pertencem à fatura corrente. Razão: lógica padrão de cartões de crédito no Brasil.

## Constraints

### Must
- Todos os modelos herdam `BaseModel` (UUID pk, created_at, updated_at, is_active)
- Soft-delete via `is_active=False` — nunca usar hard DELETE em cartões
- Tenant isolation: todo queryset deve filtrar por `request.user`
- Últimos 4 dígitos devem conter exatamente 4 caracteres numéricos
- Limite disponível = `credit_limit - soma transações vinculadas na fatura atual`
- Todas as views protegidas por `LoginRequiredMixin`
- Campos de limite e fatura ignorados para cartões de débito

### Must Not
- Não adicionar dependências externas sem listá-las aqui
- Não modificar arquivos fora do escopo de `apps/cards/`, `templates/cards/`, `tests/cards/`
- Não permitir hard-delete de cartões
- Não armazenar número completo do cartão (apenas últimos 4 dígitos)

### Out of Scope
- Integração com operadoras de cartão
- Pagamento automático de fatura
- Alertas de limite próximo do teto
- Múltiplas faturas (histórico de faturas fechadas)

## Data Model

```python
# Card — cartão de crédito ou débito do usuário
class Card(BaseModel):
    CARD_TYPE_CHOICES = [("credito", "Crédito"), ("debito", "Débito")]

    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="cards",
    )
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)  # Visa, Mastercard, Elo, etc.
    last_four_digits = models.CharField(max_length=4)
    card_type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES)
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    billing_close_day = models.IntegerField(null=True, blank=True)  # 1-31
    billing_due_day = models.IntegerField(null=True, blank=True)  # 1-31

    class Meta:
        ordering = ["name"]
        verbose_name = "Cartão"
        verbose_name_plural = "Cartões"

    def __str__(self):
        return f"{self.name} (****{self.last_four_digits})"
```

## Current State

- App directory: `apps/cards/` — existe, mas vazio (sem arquivos Python)
- Relevant existing files: nenhum arquivo no app ainda
- BaseModel: `core/models.py` — já implementado
- URL include: `core/urls.py` já possui `path('', include('apps.cards.urls'))`
- Templates base: `templates/base.html`, `templates/includes/` existem
- Tests dir: `tests/__init__.py` existe
- Patterns to follow: usar o padrão de service layer

## Tasks

### T1: Models — Criar modelo Card
**What:** Criar o modelo `Card` em `apps/cards/models.py` conforme Data Model acima. Criar `apps/cards/apps.py` com `CardsConfig` (name=`apps.cards`). Criar `apps/cards/__init__.py`.
**Files:** `apps/cards/models.py`, `apps/cards/apps.py`, `apps/cards/__init__.py`
**Depends on:** none
**Verify:** `python manage.py makemigrations cards` gera a migration inicial sem erros

### T2: Migrations — Gerar e aplicar migration inicial
**What:** Gerar a migration inicial para o app cards e aplicar ao banco.
**Files:** `apps/cards/migrations/0001_initial.py`
**Depends on:** T1
**Verify:** `python manage.py migrate` executa sem erros; tabela `cards_card` existe no banco

### T3: Service — CRUD de cartões
**What:** Implementar funções de serviço para o domínio de cartões:
- `create_card(user, name, brand, last_four_digits, card_type, credit_limit=None, billing_close_day=None, billing_due_day=None) -> Card` — cria cartão validando: últimos 4 dígitos numéricos, campos de crédito preenchidos se tipo=crédito. Levanta `ValidationError` para dados inválidos.
- `update_card(card_id, user, **kwargs) -> Card` — atualiza campos. Valida ownership e integridade dos dados.
- `deactivate_card(card_id, user) -> Card` — soft-delete via `is_active=False`.
**Files:** `apps/cards/services.py`
**Depends on:** T2
**Verify:** Testes unitários validam criação com dados válidos, rejeição de últimos 4 dígitos inválidos, e soft-delete

### T4: Selectors — Queries de leitura e cálculo de limite
**What:** Implementar selectors:
- `get_user_cards(user, active_only=True) -> QuerySet[Card]` — retorna cartões do usuário, filtrados por is_active.
- `get_card_by_id(card_id, user) -> Card` — retorna cartão por ID, validando ownership.
- `get_available_limit(card) -> Decimal` — calcula limite disponível: `credit_limit - soma das transações de saída vinculadas ao cartão no período da fatura atual`. Retorna `None` para cartões de débito.
- `get_card_transactions(card_id, user, billing_period=None) -> QuerySet[Transaction]` — retorna transações vinculadas ao cartão, opcionalmente filtradas por período de fatura.
**Files:** `apps/cards/selectors.py`
**Depends on:** T2
**Verify:** Limite disponível calculado corretamente; transações filtradas por período de fatura; tenant isolation garantida

### T5: Views + URLs — Endpoints de cartões
**What:** Implementar views para CRUD via Django Templates:
- `CardListView` (GET `/cards/`) — lista cartões ativos com limite disponível (crédito). Template: `templates/cards/card_list.html`
- `CardCreateView` (GET/POST `/cards/create/`) — formulário com campos condicionais (limite/fatura para crédito). Template: `templates/cards/card_form.html`. Redirect para list.
- `CardDetailView` (GET `/cards/<uuid:pk>/`) — detalhe do cartão com limite disponível e transações da fatura atual. Template: `templates/cards/card_detail.html`
- `CardUpdateView` (GET/POST `/cards/<uuid:pk>/edit/`) — edição. Template: `templates/cards/card_form.html`. Redirect para list.
- `CardDeleteView` (POST `/cards/<uuid:pk>/delete/`) — soft-delete. Redirect para list.

Todas protegidas com `LoginRequiredMixin`. Configurar `apps/cards/urls.py` com `app_name = "cards"`.
**Files:** `apps/cards/views.py`, `apps/cards/urls.py`
**Depends on:** T3, T4
**Verify:** `GET /cards/` retorna 200; criação de cartão de crédito exibe campos de limite; detalhe mostra limite disponível calculado

### T6: Templates — Páginas de cartões
**What:** Criar templates para o módulo:
- `templates/cards/card_list.html` — extends `base.html`. Lista cartões com nome, bandeira, últimos 4 dígitos, tipo (badge), limite disponível/total (se crédito). Botões de ação.
- `templates/cards/card_form.html` — extends `base.html`. Formulário com campos condicionais: seção de limite e fatura aparece apenas quando tipo=crédito (via JS). Validação de 4 dígitos numéricos.
- `templates/cards/card_detail.html` — extends `base.html`. Exibe dados do cartão, barra de limite (visual), lista de transações da fatura atual.
**Files:** `templates/cards/card_list.html`, `templates/cards/card_form.html`, `templates/cards/card_detail.html`
**Depends on:** T5
**Verify:** Páginas renderizam sem erros; campos condicionais funcionam; barra de limite exibe proporção correta

### T7: Serializers — Serializers DRF para API
**What:** Criar serializers para a API:
- `CardSerializer` — campos: id, name, brand, last_four_digits, card_type, credit_limit, billing_close_day, billing_due_day, available_limit (read-only, computed), created_at. O campo `available_limit` é calculado via `SerializerMethodField` chamando o selector.
- `CardCreateUpdateSerializer` — campos: name, brand, last_four_digits, card_type, credit_limit (opcional), billing_close_day (opcional), billing_due_day (opcional). Validação: 4 dígitos numéricos; campos de crédito recomendados se tipo=crédito.
**Files:** `apps/cards/serializers.py`
**Depends on:** T3, T4
**Verify:** Serializers validam dados corretamente; available_limit calculado no read; rejeita dígitos inválidos

### T8: API Views + URLs — Endpoints REST
**What:** Implementar API views com DRF:
- `CardListCreateAPIView` (GET/POST `/api/v1/cards/`) — lista cartões ativos com limite disponível; cria cartão. Requer JWT.
- `CardDetailAPIView` (GET/PUT/DELETE `/api/v1/cards/<uuid:pk>/`) — detalhe com limite disponível, atualização e soft-delete. Requer JWT.
- `CardTransactionsAPIView` (GET `/api/v1/cards/<uuid:pk>/transactions/`) — lista transações vinculadas ao cartão, opcionalmente filtradas por período de fatura. Requer JWT.

Todas com `permission_classes = [IsAuthenticated]`. Configurar `apps/cards/api_urls.py`. Incluir em `core/urls.py`: `path('api/v1/cards/', include('apps.cards.api_urls'))`.
**Files:** `apps/cards/api_views.py`, `apps/cards/api_urls.py`, `core/urls.py`
**Depends on:** T7
**Verify:** `GET /api/v1/cards/` com JWT retorna lista com available_limit; `POST` cria cartão; sem JWT retorna 401

### T9: Admin — Registro no Django Admin
**What:** Registrar modelo `Card` no Django Admin com:
- `list_display`: name, user, brand, last_four_digits, card_type, credit_limit, is_active
- `list_filter`: card_type, is_active, brand
- `search_fields`: name, user__email, last_four_digits
- `readonly_fields`: id, created_at, updated_at
**Files:** `apps/cards/admin.py`
**Depends on:** T2
**Verify:** `/admin/cards/card/` lista registros; formulário de criação funciona

### T10: Tests — Testes unitários e de integração
**What:** Implementar testes cobrindo:
- **Services:** criar cartão crédito/débito, validação de 4 dígitos, soft-delete, update com ownership check
- **Selectors:** listar cartões por usuário, cálculo de limite disponível (com e sem transações), filtro por período de fatura, tenant isolation
- **Views (SSR):** acesso autenticado vs não autenticado, CRUD completo, campos condicionais por tipo de cartão
- **API:** GET list com JWT (available_limit presente), POST create, PUT update, DELETE soft-delete, GET transactions por cartão, sem JWT → 401, tenant isolation via API
**Files:** `tests/cards/__init__.py`, `tests/cards/test_services.py`, `tests/cards/test_views.py`, `tests/cards/test_api.py`
**Depends on:** T5, T6, T8, T9
**Verify:** `pytest tests/cards/` passa com 0 falhas

## Validation

**Happy path:**
1. Usuário acessa `/cards/` — lista vazia
2. Usuário cadastra cartão de crédito: "Nubank", Mastercard, "1234", limite R$5.000, fechamento dia 3, vencimento dia 10
3. Cartão aparece na lista com limite disponível R$5.000
4. Usuário vincula uma transação de saída de R$500 ao cartão (via módulo Transactions)
5. Limite disponível atualiza para R$4.500 em tempo real
6. Usuário cadastra cartão de débito: "Itaú", Visa, "5678" — sem campos de limite/fatura
7. Detalhe do cartão de crédito exibe barra de limite e transações da fatura atual

**Edge cases:**
- Usuário informa últimos dígitos com letras ("12AB") → erro de validação
- Usuário informa 3 ou 5 dígitos → erro de validação
- Cartão de débito — campos de limite/fatura são ignorados mesmo se preenchidos
- Cartão desativado — transações vinculadas permanecem no histórico
- Usuário A não consegue acessar cartões do Usuário B → 404
- Limite disponível nunca fica negativo (exibe R$0 se gastos excedem limite)

**Commands:**
```bash
pytest tests/cards/
# Manual: cadastrar cartão de crédito e verificar limite disponível
# Manual: vincular transação e confirmar atualização do limite
# Manual: verificar /admin/cards/card/ no Django Admin
```
