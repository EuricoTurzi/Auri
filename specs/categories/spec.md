# Categories

## Why

O sistema precisa de um mecanismo de classificação flexível para transações financeiras. Categorias funcionam como tags configuráveis que permitem ao usuário organizar, filtrar e extrair relatórios segmentados. Sem categorias hardcoded — tudo é modular e definido pelo próprio usuário.

## What

Usuário autenticado pode criar, editar, listar e desativar categorias personalizadas. Cada categoria possui nome (único por usuário), descrição opcional, cor e ícone opcionais. Categorias desativadas permanecem no histórico de transações mas não aparecem nos seletores de novas transações. O sistema inicia sem categorias padrão — o usuário cria conforme sua necessidade. Todas as operações possuem endpoints API correspondentes sob `/api/v1/categories/` para integração mobile/SPA via JWT.

## Decisions

- Auth strategy (SSR): Session Auth — Django Templates.
- Auth strategy (API): JWT via `djangorestframework-simplejwt` — para mobile/SPA.
- API prefix: `/api/v1/categories/`.
- Soft-delete: `is_active=False` como padrão. Nunca hard-delete em categorias.
- Categorias flat: lista simples, sem hierarquia ou subcategorias.
- Sem categorias padrão: sistema inicia vazio após registro do usuário.
- Tenant isolation: todo queryset filtra por `request.user`.
- Unicidade: `unique_together = [("user", "name")]` para garantir nome único por usuário.

> Assumption: Cor será armazenada como string hex (ex: `#FF5733`, max_length=7). Razão: padrão comum para cores em interfaces web, compatível com CSS.

> Assumption: Ícone será armazenado como string representando o nome do ícone (ex: classe CSS ou emoji, max_length=50). Razão: permite flexibilidade na renderização sem armazenar arquivos.

## Constraints

### Must
- Todos os modelos herdam `BaseModel` (UUID pk, created_at, updated_at, is_active)
- Soft-delete via `is_active=False` — nunca usar hard DELETE em categorias
- Tenant isolation: todo queryset em modelos com escopo de usuário deve filtrar por `request.user`
- Nome da categoria único por usuário (`unique_together`)
- Todas as views protegidas por `LoginRequiredMixin`
- Categorias desativadas não aparecem nos seletores de transações

### Must Not
- Não criar categorias padrão automaticamente (nenhum seed/fixture)
- Não adicionar dependências externas sem listá-las aqui
- Não modificar arquivos fora do escopo de `apps/categories/`, `templates/categories/`, `tests/categories/`
- Não permitir hard-delete de categorias

### Out of Scope
- Subcategorias / hierarquia de categorias
- Importação/exportação de categorias
- Categorias compartilhadas entre usuários
- Integração com módulo Assistant (será tratada na spec do Assistant)

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

# Category — classificação configurável de transações
class Category(BaseModel):
    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=7, null=True, blank=True)  # hex: #FF5733
    icon = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = [("user", "name")]
        ordering = ["name"]
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.name
```

## Current State

- App directory: `apps/categories/` — existe, mas vazio (sem arquivos Python)
- Relevant existing files: nenhum arquivo no app ainda
- BaseModel: `core/models.py` — já implementado
- URL include: `core/urls.py` já possui `path('', include('apps.categories.urls'))`
- Templates base: `templates/base.html`, `templates/includes/` existem
- Tests dir: `tests/__init__.py` existe
- Patterns to follow: usar o padrão de service layer (ver `apps/accounts/services.py` quando implementado)

## Tasks

<!-- Layer order: Models → Migrations → Services → Selectors → Views/URLs → Templates → Admin → Tests -->

### T1: Models — Criar modelo Category
**What:** Criar o modelo `Category` em `apps/categories/models.py` conforme Data Model acima. Criar `apps/categories/apps.py` com `CategoriesConfig` (name=`apps.categories`). Criar `apps/categories/__init__.py`.
**Files:** `apps/categories/models.py`, `apps/categories/apps.py`, `apps/categories/__init__.py`
**Depends on:** none
**Verify:** `python manage.py makemigrations categories` gera a migration inicial sem erros

### T2: Migrations — Gerar e aplicar migration inicial
**What:** Gerar a migration inicial para o app categories e aplicar ao banco.
**Files:** `apps/categories/migrations/0001_initial.py`
**Depends on:** T1
**Verify:** `python manage.py migrate` executa sem erros; tabela `categories_category` existe no banco

### T3: Service — CRUD de categorias
**What:** Implementar funções de serviço para o domínio de categorias:
- `create_category(user, name, description=None, color=None, icon=None) -> Category` — cria categoria validando unicidade do nome por usuário. Levanta `ValidationError` se nome duplicado.
- `update_category(category_id, user, **kwargs) -> Category` — atualiza campos da categoria. Valida unicidade do nome se alterado. Levanta `PermissionError` se categoria não pertence ao usuário.
- `deactivate_category(category_id, user) -> Category` — soft-delete via `is_active=False`. Levanta `PermissionError` se não pertence ao usuário.
**Files:** `apps/categories/services.py`
**Depends on:** T2
**Verify:** Testes unitários chamam cada service com dados válidos e inválidos, assertando resultados esperados

### T4: Selectors — Queries de leitura
**What:** Implementar selectors para consultas filtradas:
- `get_user_categories(user, active_only=True) -> QuerySet[Category]` — retorna categorias do usuário, filtradas por `is_active` quando `active_only=True`. Ordenadas por nome.
- `get_category_by_id(category_id, user) -> Category` — retorna categoria por ID, validando que pertence ao usuário. Levanta `Category.DoesNotExist` se não encontrada ou não pertence ao usuário.
**Files:** `apps/categories/selectors.py`
**Depends on:** T2
**Verify:** Selector retorna apenas registros pertencentes ao usuário correto; categorias inativas são excluídas quando `active_only=True`

### T5: Views + URLs — Endpoints de categorias
**What:** Implementar views para CRUD de categorias via Django Templates:
- `CategoryListView` (GET `/categories/`) — lista categorias ativas do usuário. Template: `templates/categories/category_list.html`
- `CategoryCreateView` (GET/POST `/categories/create/`) — formulário de criação. Template: `templates/categories/category_form.html`. Redirect para list após sucesso.
- `CategoryUpdateView` (GET/POST `/categories/<uuid:pk>/edit/`) — formulário de edição. Template: `templates/categories/category_form.html` (reutiliza). Redirect para list após sucesso.
- `CategoryDeleteView` (POST `/categories/<uuid:pk>/delete/`) — soft-delete via service. Redirect para list.

Todas as views protegidas com `LoginRequiredMixin`. Configurar `apps/categories/urls.py` com `app_name = "categories"`.
**Files:** `apps/categories/views.py`, `apps/categories/urls.py`
**Depends on:** T3, T4
**Verify:** `GET /categories/` retorna 200 com lista; `POST /categories/create/` com dados válidos redireciona para list; usuário não autenticado recebe redirect para login

### T6: Templates — Páginas de categorias
**What:** Criar templates para o módulo:
- `templates/categories/category_list.html` — extends `base.html`. Lista categorias com nome, cor (preview visual), ícone, descrição. Botões de editar e excluir por item. Botão de criar nova categoria.
- `templates/categories/category_form.html` — extends `base.html`. Formulário reutilizável para criação e edição. Campos: nome, descrição, cor (input type color), ícone. Botão de salvar e cancelar.
**Files:** `templates/categories/category_list.html`, `templates/categories/category_form.html`
**Depends on:** T5
**Verify:** Páginas renderizam sem erros de template; formulário submete corretamente; cor aparece como preview visual

### T7: Serializers — Serializers DRF para API
**What:** Criar serializers para a API:
- `CategorySerializer` — campos: id, name, description, color, icon, created_at. Read-only.
- `CategoryCreateUpdateSerializer` — campos: name, description (opcional), color (opcional), icon (opcional). Validação de unicidade do nome por usuário.
**Files:** `apps/categories/serializers.py`
**Depends on:** T3
**Verify:** Serializers validam dados corretamente; rejeita nome duplicado por usuário

### T8: API Views + URLs — Endpoints REST
**What:** Implementar API views com DRF:
- `CategoryListCreateAPIView` (GET/POST `/api/v1/categories/`) — lista categorias ativas; cria categoria. Requer JWT.
- `CategoryDetailAPIView` (GET/PUT/DELETE `/api/v1/categories/<uuid:pk>/`) — detalhe, atualização e soft-delete. Requer JWT.

Todas com `permission_classes = [IsAuthenticated]`. Configurar `apps/categories/api_urls.py`. Incluir em `core/urls.py`: `path('api/v1/categories/', include('apps.categories.api_urls'))`.
**Files:** `apps/categories/api_views.py`, `apps/categories/api_urls.py`, `core/urls.py`
**Depends on:** T7
**Verify:** `GET /api/v1/categories/` com JWT retorna lista; `POST` cria categoria; nome duplicado retorna 400; sem JWT retorna 401

### T9: Admin — Registro no Django Admin
**What:** Registrar modelo `Category` no Django Admin com:
- `list_display`: name, user, color, is_active, created_at
- `list_filter`: is_active, created_at
- `search_fields`: name, user__email
- `readonly_fields`: id, created_at, updated_at
**Files:** `apps/categories/admin.py`
**Depends on:** T2
**Verify:** `/admin/categories/category/` lista registros; formulário de criação funciona end-to-end

### T10: Tests — Testes unitários e de integração
**What:** Implementar testes cobrindo:
- **Services:** criar categoria com dados válidos, criar com nome duplicado (erro), update com validação de unicidade, deactivate category, tentativa de operar categoria de outro usuário (PermissionError)
- **Selectors:** listar categorias apenas do usuário autenticado, filtrar por active_only, get_by_id com usuário correto e incorreto
- **Views (SSR):** acesso autenticado vs não autenticado, criação via POST, edição via POST, soft-delete via POST, verificar que categorias inativas não aparecem na listagem
- **API:** GET list com JWT, POST create, PUT update, DELETE soft-delete, nome duplicado → 400, sem JWT → 401, tenant isolation via API
**Files:** `tests/categories/__init__.py`, `tests/categories/test_services.py`, `tests/categories/test_views.py`, `tests/categories/test_api.py`
**Depends on:** T5, T6, T8, T9
**Verify:** `pytest tests/categories/` passa com 0 falhas

## Validation

**Happy path:**
1. Usuário autenticado acessa `/categories/` — página lista vazia (sem categorias padrão)
2. Usuário clica em "Nova Categoria" e preenche: nome="Alimentação", cor="#4CAF50", ícone="utensils"
3. Após submit, redireciona para `/categories/` com a categoria "Alimentação" listada com preview de cor verde
4. Usuário cria segunda categoria: nome="Transporte", cor="#2196F3"
5. Usuário edita "Alimentação" → altera descrição para "Gastos com comida e restaurantes"
6. Usuário exclui "Transporte" → categoria some da listagem (soft-delete)
7. No Django Admin, categoria "Transporte" aparece com `is_active=False`

**Edge cases:**
- Usuário tenta criar categoria com nome duplicado ("Alimentação") → erro de validação exibido no formulário
- Usuário A não consegue ver/editar/excluir categorias do Usuário B → 404 ou PermissionError
- Usuário tenta acessar `/categories/` sem autenticação → redirect para login
- Categoria desativada não aparece nos seletores do módulo Transactions
- Nome com espaços extras é trimado antes da validação de unicidade

**Commands:**
```bash
pytest tests/categories/
# Manual: acessar /categories/ no navegador logado e verificar CRUD completo
# Manual: verificar /admin/categories/category/ no Django Admin
```
