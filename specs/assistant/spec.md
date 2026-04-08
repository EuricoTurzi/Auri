# Assistant

## Why

Registrar transações via formulário pode ser tedioso e criar barreira de uso. O módulo Assistant elimina essa fricção ao permitir que o usuário registre transações em linguagem natural — por texto ou áudio — sem precisar entender termos financeiros. Um agente de IA interpreta a intenção, extrai os dados, e cria a transação somente após confirmação explícita do usuário.

## What

Interface conversacional onde o usuário digita ou grava áudio em linguagem natural (ex: "gastei 50 reais no mercado ontem"). O áudio é transcrito via OpenAI Whisper, o texto é interpretado via OpenAI GPT que extrai os campos da transação, mapeia contra categorias e cartões do usuário, e solicita dados faltantes. Antes de salvar, um preview/card é exibido para o usuário confirmar, alterar ou cancelar. Todas as interações são registradas para rastreabilidade. Todas as operações possuem endpoints API correspondentes sob `/api/v1/assistant/` para integração mobile/SPA via JWT.

## Decisions

- Auth strategy (SSR): Session Auth — Django Templates.
- Auth strategy (API): JWT via `djangorestframework-simplejwt` — para mobile/SPA.
- API prefix: `/api/v1/assistant/`.
- LLM: OpenAI GPT para interpretação de linguagem natural.
- Transcrição de áudio: OpenAI Whisper API.
- Gravação de áudio: MediaRecorder API do navegador (JavaScript nativo).
- Fluxo conversacional: multi-turn — se dados obrigatórios faltam, a LLM solicita ao usuário.
- A LLM nunca assume ou inventa dados — trabalha exclusivamente com o que o usuário informou.
- Preview obrigatório antes de salvar — nenhuma transação criada sem confirmação explícita.
- Soft-delete para `AssistantInteraction`.
- Tenant isolation: todo queryset filtra por `request.user`.

> Assumption: A comunicação com OpenAI GPT será via `openai` Python SDK (versão >=1.0). Razão: SDK oficial, amplamente suportado, com tipagem.

> Assumption: O áudio será enviado como arquivo via POST multipart para o backend, que encaminha para a Whisper API. Razão: manter a API key no servidor, nunca expor no frontend.

> Assumption: O prompt do GPT receberá como contexto a lista de categorias e cartões ativos do usuário para mapeamento. Razão: permitir que a LLM faça matching correto sem precisar de chamadas extras.

> Assumption: O fluxo conversacional será gerenciado via sessão Django (armazenando o histórico de mensagens por interação). Razão: evita complexidade de WebSockets no MVP; compatível com SSR.

## Constraints

### Must
- Todos os modelos herdam `BaseModel` (UUID pk, created_at, updated_at, is_active)
- Soft-delete via `is_active=False` para AssistantInteraction
- Tenant isolation: todo queryset deve filtrar por `request.user`
- Todas as views protegidas por `LoginRequiredMixin`
- API key da OpenAI armazenada em variável de ambiente (`OPENAI_API_KEY`), nunca no código
- Preview/card obrigatório antes de criar transação — nunca salvar automaticamente
- LLM não pode inventar dados — solicitar informações faltantes ao usuário
- Áudio processado no backend (API key nunca exposta no frontend)

### Must Not
- Não adicionar dependências externas além de `openai` (Python SDK)
- Não modificar arquivos fora do escopo de `apps/assistant/`, `templates/assistant/`, `tests/assistant/`
- Não armazenar áudio original em disco (apenas a transcrição é persistida)
- Não criar transação sem confirmação explícita do usuário
- Não expor API key da OpenAI no frontend

### Out of Scope
- Histórico de conversas anteriores (cada interação é independente)
- Suporte a múltiplos idiomas (apenas pt-br no MVP)
- Integração com outros LLMs além de OpenAI
- Comandos de consulta via Assistant (ex: "quanto gastei esse mês") — MVP focado apenas em registro
- Streaming de resposta da LLM (resposta completa no MVP)

## Data Model

```python
# AssistantInteraction — registro de interação com o assistente de IA
class AssistantInteraction(BaseModel):
    INPUT_TYPE_CHOICES = [("texto", "Texto"), ("audio", "Áudio")]
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("confirmado", "Confirmado"),
        ("cancelado", "Cancelado"),
    ]

    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="assistant_interactions",
    )
    input_type = models.CharField(max_length=10, choices=INPUT_TYPE_CHOICES)
    input_content = models.TextField(
        help_text="Texto digitado pelo usuário ou transcrição do áudio"
    )
    llm_response = models.JSONField(
        default=dict,
        help_text="Dados extraídos pela LLM: {name, amount, type, category, date, description, card}",
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="pendente"
    )
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_interactions",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Interação do Assistente"
        verbose_name_plural = "Interações do Assistente"

    def __str__(self):
        return f"{self.user.email} - {self.input_type} - {self.status}"
```

## Current State

- App directory: `apps/assistant/` — existe, mas vazio (sem arquivos Python)
- Relevant existing files: nenhum arquivo no app ainda
- BaseModel: `core/models.py` — já implementado
- URL include: `core/urls.py` já possui `path('', include('apps.assistant.urls'))`
- Templates base: `templates/base.html`, `templates/includes/` existem
- Tests dir: `tests/__init__.py` existe
- Dependências: módulos Transactions, Categories e Cards devem estar implementados (para criar transação e mapear contexto)
- Patterns to follow: usar o padrão de service layer

## Tasks

### T1: Models — Criar modelo AssistantInteraction
**What:** Criar o modelo `AssistantInteraction` em `apps/assistant/models.py` conforme Data Model acima. Criar `apps/assistant/apps.py` com `AssistantConfig` (name=`apps.assistant`). Criar `apps/assistant/__init__.py`.
**Files:** `apps/assistant/models.py`, `apps/assistant/apps.py`, `apps/assistant/__init__.py`
**Depends on:** none
**Verify:** `python manage.py makemigrations assistant` gera a migration inicial sem erros

### T2: Migrations — Gerar e aplicar migration inicial
**What:** Gerar a migration inicial para o app assistant e aplicar ao banco.
**Files:** `apps/assistant/migrations/0001_initial.py`
**Depends on:** T1
**Verify:** `python manage.py migrate` executa sem erros; tabela `assistant_assistantinteraction` existe no banco

### T3: Service — Transcrição de áudio (Whisper)
**What:** Implementar serviço de transcrição:
- `transcribe_audio(audio_file) -> str` — recebe arquivo de áudio (UploadedFile), envia para OpenAI Whisper API, retorna texto transcrito. Levanta `ServiceError` se a API falhar.
- Configuração: usar `OPENAI_API_KEY` de `settings` ou `os.environ`.
**Files:** `apps/assistant/services.py`
**Depends on:** T2
**Verify:** Teste unitário com mock da API Whisper valida que áudio é enviado e transcrição retornada

### T4: Service — Interpretação de texto (GPT)
**What:** Implementar serviço de interpretação via LLM:
- `interpret_transaction(user, text) -> dict` — envia texto para OpenAI GPT com prompt estruturado contendo:
  - Instrução para extrair campos: name, amount, type (entrada/saída), category, date, description, card.
  - Lista de categorias ativas do usuário (nomes e IDs) como contexto.
  - Lista de cartões ativos do usuário (nomes e IDs) como contexto.
  - Instrução para retornar JSON estruturado.
  - Instrução para indicar campos faltantes com `null` e incluir `missing_fields: [lista]` quando dados obrigatórios não foram fornecidos.
- Retorna dict com os dados extraídos e lista de campos faltantes (se houver).
- `build_system_prompt(user) -> str` — monta o prompt do sistema com categorias e cartões do usuário.
**Files:** `apps/assistant/services.py`
**Depends on:** T3, Categories T2, Cards T2
**Verify:** Teste com mock do GPT valida extração de dados de texto em linguagem natural; valida que campos faltantes são identificados

### T5: Service — Confirmação e criação de transação
**What:** Implementar serviço de confirmação:
- `confirm_interaction(interaction_id, user, adjusted_data=None) -> Transaction` — recebe o ID da interação pendente. Se `adjusted_data` fornecido, usa os dados ajustados; senão, usa `llm_response`. Chama o service de Transactions (`create_transaction`) para criar a transação. Atualiza `AssistantInteraction` com `status="confirmado"` e vincula a `transaction` criada.
- `cancel_interaction(interaction_id, user) -> AssistantInteraction` — marca como `status="cancelado"`.
- `create_interaction(user, input_type, input_content, llm_response) -> AssistantInteraction` — cria registro da interação com `status="pendente"`.
**Files:** `apps/assistant/services.py`
**Depends on:** T4, Transactions T3
**Verify:** Confirmação cria transação e atualiza status; cancelamento atualiza status sem criar transação

### T6: Selectors — Queries de leitura
**What:** Implementar selectors:
- `get_user_interactions(user, status=None) -> QuerySet[AssistantInteraction]` — retorna interações do usuário, opcionalmente filtradas por status.
- `get_interaction_by_id(interaction_id, user) -> AssistantInteraction` — retorna interação por ID, validando ownership.
**Files:** `apps/assistant/selectors.py`
**Depends on:** T2
**Verify:** Selector retorna apenas registros do usuário correto; filtro por status funciona

### T7: Views + URLs — Interface do assistente
**What:** Implementar views:
- `AssistantView` (GET `/assistant/`) — página principal do assistente com input de texto e botão de gravação de áudio. Template: `templates/assistant/assistant.html`.
- `AssistantTextView` (POST `/assistant/text/`) — recebe texto do usuário, chama `interpret_transaction`, cria `AssistantInteraction` com status pendente. Se dados completos, retorna preview/card. Se faltam dados, retorna pergunta da LLM. Resposta via JSON para atualização dinâmica da página.
- `AssistantAudioView` (POST `/assistant/audio/`) — recebe arquivo de áudio (multipart), chama `transcribe_audio`, depois segue mesmo fluxo do texto. Resposta via JSON.
- `AssistantConfirmView` (POST `/assistant/confirm/<uuid:pk>/`) — confirma interação pendente. Aceita dados ajustados opcionalmente. Cria transação. Resposta via JSON.
- `AssistantCancelView` (POST `/assistant/cancel/<uuid:pk>/`) — cancela interação. Resposta via JSON.

Todas protegidas com `LoginRequiredMixin`. Configurar `apps/assistant/urls.py` com `app_name = "assistant"`.
**Files:** `apps/assistant/views.py`, `apps/assistant/urls.py`
**Depends on:** T3, T4, T5, T6
**Verify:** `GET /assistant/` retorna 200; POST text retorna JSON com preview; POST audio transcreve e retorna preview; confirm cria transação

### T8: Templates — Interface do assistente
**What:** Criar template principal:
- `templates/assistant/assistant.html` — extends `base.html`. Contém:
  - Área de chat/conversa para exibir mensagens do usuário e respostas da LLM.
  - Input de texto com botão de enviar.
  - Botão de gravação de áudio (MediaRecorder API via JS). Indicador visual de gravação ativa.
  - Card/preview de transação renderizado dinamicamente (via JS) ao receber resposta com dados completos. Exibe: nome, valor, tipo, categoria, data, cartão, descrição. Botões: Confirmar, Editar, Cancelar.
  - Formulário de edição inline no card (campos editáveis antes de confirmar).
  - JavaScript para: POST assíncrono (fetch), gravação de áudio, renderização dinâmica de respostas e preview.
**Files:** `templates/assistant/assistant.html`
**Depends on:** T7
**Verify:** Página renderiza sem erros; input de texto envia e recebe resposta; gravação de áudio funciona no navegador; preview exibe dados corretamente

### T9: Serializers — Serializers DRF para API
**What:** Criar serializers para a API:
- `AssistantInteractionSerializer` — campos: id, input_type, input_content, llm_response, status, transaction (id, nullable), created_at. Read-only.
- `TextInputSerializer` — campos: message (TextField). Para input de texto via API.
- `AudioInputSerializer` — campos: audio (FileField). Para upload de áudio via API.
- `ConfirmSerializer` — campos: adjusted_data (JSONField, opcional). Para confirmação com ajustes opcionais.
- `TransactionPreviewSerializer` — campos: name, amount, type, category (id+name), date, description, card (id+name, nullable), missing_fields (list). Read-only, para exibir preview.
**Files:** `apps/assistant/serializers.py`
**Depends on:** T5
**Verify:** Serializers validam dados corretamente; PreviewSerializer exibe dados extraídos pela LLM

### T10: API Views + URLs — Endpoints REST
**What:** Implementar API views com DRF:
- `AssistantTextAPIView` (POST `/api/v1/assistant/text/`) — recebe texto, processa via LLM, retorna preview ou pergunta. Requer JWT.
- `AssistantAudioAPIView` (POST `/api/v1/assistant/audio/`) — recebe áudio (multipart), transcreve via Whisper, processa via LLM, retorna preview ou pergunta. Requer JWT.
- `AssistantConfirmAPIView` (POST `/api/v1/assistant/confirm/<uuid:pk>/`) — confirma interação, cria transação. Aceita dados ajustados. Requer JWT.
- `AssistantCancelAPIView` (POST `/api/v1/assistant/cancel/<uuid:pk>/`) — cancela interação. Requer JWT.
- `AssistantHistoryAPIView` (GET `/api/v1/assistant/history/`) — lista interações do usuário. Requer JWT.

Todas com `permission_classes = [IsAuthenticated]`. Configurar `apps/assistant/api_urls.py`. Incluir em `core/urls.py`: `path('api/v1/assistant/', include('apps.assistant.api_urls'))`.
**Files:** `apps/assistant/api_views.py`, `apps/assistant/api_urls.py`, `core/urls.py`
**Depends on:** T9
**Verify:** `POST /api/v1/assistant/text/` com JWT retorna preview; `POST audio/` transcreve e retorna preview; confirm cria transação; sem JWT retorna 401

### T11: Admin — Registro no Django Admin
**What:** Registrar modelo `AssistantInteraction` no Django Admin com:
- `list_display`: user, input_type, status, transaction, created_at
- `list_filter`: input_type, status, created_at
- `search_fields`: user__email, input_content
- `readonly_fields`: id, created_at, updated_at, llm_response
**Files:** `apps/assistant/admin.py`
**Depends on:** T2
**Verify:** `/admin/assistant/assistantinteraction/` lista registros; detalhes exibem llm_response formatado

### T12: Tests — Testes unitários e de integração
**What:** Implementar testes cobrindo:
- **Services (transcrição):** mock Whisper API, validar envio de áudio e retorno de texto
- **Services (interpretação):** mock GPT API, validar extração de campos de textos variados ("gastei 50 no mercado", "recebi 3000 de salário"), validar identificação de campos faltantes, validar que categorias/cartões do usuário são passados no prompt
- **Services (confirmação):** confirmar interação cria transação corretamente, confirmar com dados ajustados usa dados novos, cancelar atualiza status
- **Selectors:** tenant isolation, filtro por status
- **Views (SSR):** POST text retorna preview JSON, POST audio retorna preview JSON (mock Whisper), confirm cria transação, cancel atualiza status, acesso não autenticado → redirect
- **API:** POST text via API com JWT, POST audio via API com JWT (mock Whisper), confirm via API, cancel via API, GET history, sem JWT → 401, tenant isolation via API
**Files:** `tests/assistant/__init__.py`, `tests/assistant/test_services.py`, `tests/assistant/test_views.py`, `tests/assistant/test_api.py`
**Depends on:** T8, T10, T11
**Verify:** `pytest tests/assistant/` passa com 0 falhas

## Validation

**Happy path (texto):**
1. Usuário acessa `/assistant/` — interface com input de texto e botão de áudio
2. Usuário digita: "gastei 50 reais no mercado ontem"
3. LLM interpreta e retorna preview: nome="Mercado", valor=R$50, tipo=saída, categoria="Alimentação" (mapeada), data=ontem
4. Usuário confirma → transação criada no módulo Transactions
5. Feedback de sucesso exibido na interface

**Happy path (áudio):**
1. Usuário clica no botão de gravação e fala: "recebi três mil de salário dia primeiro"
2. Whisper transcreve → texto enviado para GPT
3. LLM retorna preview: nome="Salário", valor=R$3.000, tipo=entrada, data=01 do mês atual
4. LLM identifica que categoria não foi informada → solicita ao usuário
5. Usuário responde: "categoria Renda"
6. Preview atualizado com categoria → usuário confirma → transação criada

**Edge cases:**
- Usuário diz "comprei algo" sem valor → LLM solicita: "Qual foi o valor da compra?"
- Usuário menciona categoria inexistente → LLM solicita esclarecimento com lista de categorias disponíveis
- Usuário menciona cartão inexistente → LLM solicita esclarecimento com lista de cartões
- Usuário cancela preview → AssistantInteraction marcada como "cancelado", nenhuma transação criada
- Usuário edita preview (altera valor) → dados ajustados usados na criação
- Áudio inaudível/ruído → Whisper retorna texto parcial → LLM solicita dados faltantes
- Usuário não autenticado → redirect para login
- Usuário A não acessa interações do Usuário B → tenant isolation

**Commands:**
```bash
pytest tests/assistant/
# Manual: acessar /assistant/ e testar input de texto com frases variadas
# Manual: testar gravação de áudio e transcrição
# Manual: verificar preview, edição e confirmação
# Manual: verificar /admin/assistant/assistantinteraction/ no Django Admin
```
