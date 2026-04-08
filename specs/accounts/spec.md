# Accounts

## Why

Todo o sistema depende de autenticação e isolamento de dados por usuário. Sem o módulo Accounts, nenhum outro módulo funciona. Ele garante que cada usuário possua seu próprio ambiente, com registro seguro (senha temporária por e-mail), troca obrigatória de senha no primeiro acesso, e autenticação OAuth via Google para conveniência.

## What

Usuário se registra informando nickname e e-mail. O sistema gera uma senha temporária e a envia por e-mail. No primeiro login, o sistema obriga a troca de senha. OAuth via Google é suportado como alternativa. Sessões Django para SSR e JWT (via DRF SimpleJWT) para API mobile/SPA coexistem. Todas as operações de autenticação possuem endpoints API correspondentes sob `/api/v1/accounts/`.

## Decisions

- Auth strategy (SSR): Session Auth — Django Templates.
- Auth strategy (API): JWT via `djangorestframework-simplejwt` — para mobile/SPA.
- OAuth: Google OAuth 2.0 via `django-allauth` (provider Google).
- Senha temporária gerada com `django.utils.crypto.get_random_string`.
- E-mail de primeiro acesso enviado via Django `send_mail`.
- Troca obrigatória de senha controlada por flag `is_first_access=True`.
- Tenant isolation: todo queryset filtra por `request.user` nos demais módulos.
- API prefix: `/api/v1/accounts/`.

> Assumption: `django-allauth` será utilizado para OAuth com Google. Razão: biblioteca madura, amplamente adotada, suporte nativo a múltiplos providers e compatível com DRF via `dj-rest-auth`.

> Assumption: Para API OAuth, `dj-rest-auth` com `allauth` será utilizado para expor endpoints REST de login social. Razão: integração padrão entre DRF e allauth.

> Assumption: Nickname max_length=50 e deve aceitar apenas alfanuméricos, underscore e hífen. Razão: evitar caracteres especiais que compliquem URLs ou exibição.

## Constraints

### Must
- Todos os modelos herdam `BaseModel` (UUID pk, created_at, updated_at, is_active)
- Soft-delete via `is_active=False` para CustomUser
- E-mail único no sistema (`unique=True`)
- Nickname único no sistema (`unique=True`)
- Senha temporária NUNCA retornada na resposta da API ou view — enviada exclusivamente por e-mail
- Primeiro acesso obriga troca de senha (`is_first_access=True`)
- Todas as views SSR protegidas por `LoginRequiredMixin` (exceto login/registro)
- Todas as API views protegidas por `IsAuthenticated` + JWT (exceto registro/login/token)
- API endpoints sob `/api/v1/accounts/`

### Must Not
- Não adicionar dependências além das listadas: `djangorestframework`, `djangorestframework-simplejwt`, `django-allauth`, `dj-rest-auth`
- Não modificar arquivos fora do escopo de `apps/accounts/`, `templates/accounts/`, `tests/accounts/`
- Não armazenar senha temporária em plain text no banco (usar `set_password`)
- Não retornar senha temporária em nenhuma resposta HTTP

### Out of Scope
- Recuperação de senha (reset password) — será spec separada
- Perfil do usuário (foto, dados pessoais estendidos)
- Autenticação com outros providers OAuth além de Google
- Two-factor authentication (2FA)

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

# CustomUser — usuário da plataforma
class CustomUser(BaseModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50, unique=True)
    is_first_access = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    objects = CustomUserManager()

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.email
```

## Current State

- App directory: `apps/accounts/` — existe com arquivos vazios: `__init__.py`, `admin.py`, `apps.py`, `models.py`, `services.py`, `urls.py`, `views.py`
- BaseModel: `core/models.py` — já implementado
- URL include: `core/urls.py` já possui `path('', include('apps.accounts.urls'))`
- Templates base: `templates/base.html`, `templates/includes/` existem
- Tests dir: `tests/__init__.py` existe
- Patterns to follow: este é o primeiro app a ser implementado — definirá o padrão para os demais

## Tasks

<!-- Layer order: Models → Migrations → Services → Selectors → Views/URLs → Templates → API → Admin → Tests -->

### T1: Models — Criar modelo CustomUser e CustomUserManager
**What:** Criar `CustomUser` (herda BaseModel + AbstractBaseUser + PermissionsMixin) e `CustomUserManager` (herda BaseUserManager) em `apps/accounts/models.py` conforme Data Model acima. O manager deve implementar `create_user(email, nickname, password=None)` e `create_superuser(email, nickname, password)`. Atualizar `apps/accounts/apps.py` com `AccountsConfig` (name=`apps.accounts`). Configurar `AUTH_USER_MODEL = "accounts.CustomUser"` em `core/settings/base.py`.
**Files:** `apps/accounts/models.py`, `apps/accounts/apps.py`, `core/settings/base.py`
**Depends on:** none
**Verify:** `python manage.py makemigrations accounts` gera a migration inicial sem erros

### T2: Migrations — Gerar e aplicar migration inicial
**What:** Gerar a migration inicial para o app accounts e aplicar ao banco.
**Files:** `apps/accounts/migrations/0001_initial.py`
**Depends on:** T1
**Verify:** `python manage.py migrate` executa sem erros; tabela `accounts_customuser` existe no banco; `python manage.py createsuperuser` funciona

### T3: Service — Registro de usuário
**What:** Implementar funções de serviço para registro:
- `register_user(email, nickname) -> CustomUser` — valida unicidade de e-mail e nickname. Gera senha temporária com `get_random_string(length=12)`. Cria usuário com `is_first_access=True` usando `set_password`. Dispara e-mail com senha temporária, instruções de login e aviso de troca obrigatória. Retorna o usuário criado (sem a senha).
- `generate_temporary_password() -> str` — gera senha aleatória segura.
- `send_first_access_email(user, temporary_password)` — envia e-mail formatado com senha, instruções e aviso.
**Files:** `apps/accounts/services.py`
**Depends on:** T2
**Verify:** Teste unitário cria usuário, valida `is_first_access=True`, valida que e-mail foi enviado (mock), valida que senha não é retornada na resposta

### T4: Service — Troca de senha no primeiro acesso
**What:** Implementar serviço de troca de senha:
- `change_first_access_password(user, new_password) -> CustomUser` — valida que `is_first_access=True`. Atualiza senha via `set_password`. Marca `is_first_access=False`. Retorna usuário atualizado.
- Validação: senha deve ter mínimo 8 caracteres.
**Files:** `apps/accounts/services.py`
**Depends on:** T3
**Verify:** Após troca, `is_first_access=False`; senha antiga não funciona; nova senha funciona via `check_password`

### T5: Middleware — Redirecionamento de primeiro acesso
**What:** Criar middleware que intercepta requests de usuários com `is_first_access=True`:
- Se usuário autenticado e `is_first_access=True` e URL não é a página de troca de senha nem logout → redireciona para página de troca de senha.
- Registrar middleware em `MIDDLEWARE` no settings.
**Files:** `apps/accounts/middleware.py`, `core/settings/base.py`
**Depends on:** T4
**Verify:** Usuário com `is_first_access=True` é redirecionado para troca de senha em qualquer URL acessada

### T6: Selectors — Queries de leitura
**What:** Implementar selectors:
- `get_user_by_email(email) -> CustomUser` — busca usuário por e-mail.
- `get_user_by_id(user_id) -> CustomUser` — busca usuário por UUID.
**Files:** `apps/accounts/selectors.py`
**Depends on:** T2
**Verify:** Selectors retornam usuário correto; levantam `CustomUser.DoesNotExist` para IDs/e-mails inexistentes

### T7: Views + URLs (SSR) — Login, registro e troca de senha
**What:** Implementar views Django Templates:
- `LoginView` (GET/POST `/accounts/login/`) — formulário de login com e-mail e senha. Template: `templates/accounts/login.html`. Redirect para dashboard após sucesso.
- `RegisterView` (GET/POST `/accounts/register/`) — formulário com nickname e e-mail. Template: `templates/accounts/register.html`. Redirect para login com mensagem de sucesso após registro.
- `ChangePasswordView` (GET/POST `/accounts/change-password/`) — formulário de troca de senha (primeiro acesso). Template: `templates/accounts/change_password.html`. Protegida por `LoginRequiredMixin`. Redirect para dashboard após troca.
- `LogoutView` (POST `/accounts/logout/`) — encerra sessão. Redirect para login.

Configurar `apps/accounts/urls.py` com `app_name = "accounts"`.
**Files:** `apps/accounts/views.py`, `apps/accounts/urls.py`
**Depends on:** T3, T4, T5, T6
**Verify:** `GET /accounts/login/` retorna 200; registro cria usuário e envia e-mail; login com senha temporária redireciona para troca de senha

### T8: OAuth — Configuração Google OAuth
**What:** Configurar `django-allauth` para OAuth com Google:
- Instalar e configurar `django-allauth` no settings: `INSTALLED_APPS`, `AUTHENTICATION_BACKENDS`, `SOCIALACCOUNT_PROVIDERS` (Google com escopo email+profile).
- Adicionar URLs do allauth em `core/urls.py`: `path('accounts/', include('allauth.urls'))`.
- Configurar callback: após OAuth bem-sucedido, marcar `is_first_access=False` (não precisa trocar senha para OAuth).
- Adapter customizado `apps/accounts/adapters.py` para definir `is_first_access=False` em usuários criados via OAuth.
**Files:** `apps/accounts/adapters.py`, `core/settings/base.py`, `core/urls.py`
**Depends on:** T7
**Verify:** Login com Google cria usuário com `is_first_access=False`; redirect para dashboard sem tela de troca de senha

### T9: Templates — Páginas de autenticação
**What:** Criar templates:
- `templates/accounts/login.html` — extends `base.html`. Formulário de login (e-mail + senha). Botão "Entrar com Google" (OAuth). Links para registro.
- `templates/accounts/register.html` — extends `base.html`. Formulário (nickname + e-mail). Mensagem de sucesso orientando verificar e-mail.
- `templates/accounts/change_password.html` — extends `base.html`. Formulário de nova senha com confirmação. Mensagem explicando a troca obrigatória.
**Files:** `templates/accounts/login.html`, `templates/accounts/register.html`, `templates/accounts/change_password.html`
**Depends on:** T7
**Verify:** Páginas renderizam sem erros; formulários submetem corretamente; botão OAuth redireciona para Google

### T10: Serializers — Serializers DRF para API
**What:** Criar serializers para a API:
- `RegisterSerializer` — campos: email, nickname. Valida unicidade. Não retorna senha.
- `LoginSerializer` — campos: email, password. Valida credenciais.
- `ChangePasswordSerializer` — campos: new_password, confirm_password. Valida match e min 8 chars.
- `UserSerializer` — campos: id, email, nickname, is_first_access, phone_number, created_at. Read-only.
**Files:** `apps/accounts/serializers.py`
**Depends on:** T3, T4
**Verify:** Serializers validam dados corretamente; RegisterSerializer não inclui campo de senha no output

### T11: API Views + URLs — Endpoints REST
**What:** Implementar API views com DRF:
- `RegisterAPIView` (POST `/api/v1/accounts/register/`) — registra usuário, retorna UserSerializer. Sem autenticação.
- `LoginAPIView` (POST `/api/v1/accounts/login/`) — retorna JWT tokens (access + refresh) via SimpleJWT.
- `TokenRefreshAPIView` (POST `/api/v1/accounts/token/refresh/`) — refresh do JWT.
- `ChangePasswordAPIView` (POST `/api/v1/accounts/change-password/`) — troca senha no primeiro acesso. Requer JWT.
- `MeAPIView` (GET `/api/v1/accounts/me/`) — retorna dados do usuário autenticado. Requer JWT.
- `GoogleLoginAPIView` (POST `/api/v1/accounts/google/`) — login OAuth via Google (recebe token do provider, retorna JWT). Via `dj-rest-auth`.

Configurar `apps/accounts/api_urls.py` com prefixo. Incluir em `core/urls.py`: `path('api/v1/accounts/', include('apps.accounts.api_urls'))`.
**Files:** `apps/accounts/api_views.py`, `apps/accounts/api_urls.py`, `core/urls.py`
**Depends on:** T10, T8
**Verify:** `POST /api/v1/accounts/register/` retorna 201; `POST /api/v1/accounts/login/` retorna JWT; `GET /api/v1/accounts/me/` com JWT retorna dados do usuário

### T12: Admin — Registro no Django Admin
**What:** Registrar modelo `CustomUser` no Django Admin com:
- `list_display`: email, nickname, is_first_access, is_active, is_staff, created_at
- `list_filter`: is_active, is_first_access, is_staff
- `search_fields`: email, nickname
- `readonly_fields`: id, created_at, updated_at
- Usar `UserAdmin` como base para formulários de criação/edição com campos de senha.
**Files:** `apps/accounts/admin.py`
**Depends on:** T2
**Verify:** `/admin/accounts/customuser/` lista registros; criação e edição funcionam

### T13: Tests — Testes unitários e de integração
**What:** Implementar testes cobrindo:
- **Services:** registro com dados válidos, e-mail duplicado (erro), nickname duplicado (erro), envio de e-mail (mock), troca de senha no primeiro acesso, tentativa de troca com `is_first_access=False`
- **Middleware:** redirect de primeiro acesso, usuário já trocou senha passa direto
- **Views (SSR):** login/register/change-password GET e POST, logout, OAuth redirect
- **API:** POST register, POST login (JWT), token refresh, GET me com JWT, change-password via API, Google OAuth via API (mock)
- **Serializers:** validações de unicidade, formato, senha
**Files:** `tests/accounts/__init__.py`, `tests/accounts/test_services.py`, `tests/accounts/test_views.py`, `tests/accounts/test_api.py`
**Depends on:** T7, T9, T11, T12
**Verify:** `pytest tests/accounts/` passa com 0 falhas

## Validation

**Happy path (SSR):**
1. Usuário acessa `/accounts/register/` — preenche nickname="joao" e email="joao@email.com"
2. Sistema cria usuário, envia e-mail com senha temporária
3. Usuário acessa `/accounts/login/` — loga com e-mail e senha temporária
4. Middleware detecta `is_first_access=True` → redireciona para `/accounts/change-password/`
5. Usuário define nova senha → `is_first_access=False` → redirect para dashboard
6. Próximos logins vão direto para o dashboard

**Happy path (OAuth):**
1. Usuário acessa `/accounts/login/` e clica "Entrar com Google"
2. Redirect para Google → autoriza → callback cria usuário com `is_first_access=False`
3. Redirect direto para dashboard (sem tela de troca de senha)

**Happy path (API):**
1. `POST /api/v1/accounts/register/` com `{email, nickname}` → 201 + e-mail enviado
2. `POST /api/v1/accounts/login/` com `{email, password_temporaria}` → JWT tokens
3. `POST /api/v1/accounts/change-password/` com JWT + `{new_password}` → 200
4. `GET /api/v1/accounts/me/` com JWT → dados do usuário

**Edge cases:**
- E-mail duplicado no registro → erro 400 com mensagem na UI e na API
- Nickname duplicado → erro 400
- Login com senha errada → erro 401
- Acesso a qualquer URL com `is_first_access=True` → redirect para troca de senha (SSR) ou 403 com mensagem (API)
- Senha nova com menos de 8 caracteres → erro de validação
- Token JWT expirado → 401 com mensagem de refresh
- Usuário desativado (`is_active=False`) → login negado

**Commands:**
```bash
pytest tests/accounts/
# Manual: registrar usuário e verificar e-mail no console (dev)
# Manual: login com senha temporária e verificar redirect para troca
# Manual: login com Google e verificar criação sem first_access
# Manual: testar endpoints API com curl/httpie
```
