# Reports

## Why

O usuário precisa de visibilidade consolidada sobre suas finanças e da capacidade de extrair seus dados a qualquer momento. O módulo Reports combina um dashboard visual com gráficos interativos e exportação de dados em múltiplos formatos, além de agendamento de relatórios periódicos por e-mail — garantindo que o usuário tenha controle total sobre suas informações financeiras.

## What

Dashboard visual com métricas financeiras (entradas, saídas, saldo, distribuição por categoria, evolução temporal, gastos por cartão) e filtros combinados (período, categoria, tipo, cartão). Exportação dos dados filtrados em CSV, Excel e PDF. Agendamento de relatórios automáticos por e-mail com frequência semanal, quinzenal ou mensal. Todas as operações possuem endpoints API correspondentes sob `/api/v1/reports/` para integração mobile/SPA via JWT.

## Decisions

- Auth strategy (SSR): Session Auth — Django Templates.
- Auth strategy (API): JWT via `djangorestframework-simplejwt` — para mobile/SPA.
- API prefix: `/api/v1/reports/`.
- Gráficos: Chart.js renderizado via template (sem dependência de SPA).
- Exportação Excel: `openpyxl`.
- Exportação PDF: `weasyprint` (ou `reportlab`).
- Exportação CSV: módulo `csv` nativo do Python.
- Agendamento: Celery Beat para execução de tasks periódicas.
- Soft-delete para `ScheduledReport`.
- Tenant isolation: todo queryset filtra por `request.user`.
- Filtros armazenados como JSONField no ScheduledReport.

> Assumption: Chart.js será carregado via CDN no template. Razão: não requer build tooling e é compatível com SSR via Django Templates.

> Assumption: Celery + Redis como broker para tasks assíncronas. Razão: stack padrão Django para processamento de tarefas em background; Redis já disponível via Docker.

> Assumption: E-mails de relatório agendado serão enviados via Django `send_mail` com o arquivo como anexo. Razão: reaproveita configuração de e-mail já existente no módulo Accounts.

## Constraints

### Must
- Todos os modelos herdam `BaseModel` (UUID pk, created_at, updated_at, is_active)
- Soft-delete via `is_active=False` para ScheduledReport
- Tenant isolation: todo queryset deve filtrar por `request.user`
- Exportação deve respeitar os filtros aplicados no momento da extração
- Todas as views protegidas por `LoginRequiredMixin`
- Relatórios agendados devem calcular `next_send_at` automaticamente

### Must Not
- Não adicionar dependências externas além das listadas (openpyxl, weasyprint, celery, redis)
- Não modificar arquivos fora do escopo de `apps/reports/`, `templates/reports/`, `tests/reports/`
- Não permitir relatório agendado sem pelo menos um filtro configurado
- Não expor dados de outros usuários em nenhuma circunstância

### Out of Scope
- Relatórios compartilhados entre usuários
- Dashboard customizável (drag & drop de widgets)
- Exportação em OFX ou outros formatos bancários
- Envio de relatórios via WhatsApp/Telegram

## Data Model

```python
# ScheduledReport — relatório agendado para envio periódico por e-mail
class ScheduledReport(BaseModel):
    FREQUENCY_CHOICES = [
        ("semanal", "Semanal"),
        ("quinzenal", "Quinzenal"),
        ("mensal", "Mensal"),
    ]
    FORMAT_CHOICES = [
        ("csv", "CSV"),
        ("xlsx", "Excel"),
        ("pdf", "PDF"),
    ]

    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="scheduled_reports",
    )
    name = models.CharField(max_length=150)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    export_format = models.CharField(max_length=5, choices=FORMAT_CHOICES)
    filters = models.JSONField(
        default=dict,
        help_text="Filtros configurados: {period_start, period_end, category_ids, type, card_ids}",
    )
    last_sent_at = models.DateTimeField(null=True, blank=True)
    next_send_at = models.DateTimeField()

    class Meta:
        ordering = ["next_send_at"]
        verbose_name = "Relatório Agendado"
        verbose_name_plural = "Relatórios Agendados"

    def __str__(self):
        return f"{self.name} - {self.frequency} ({self.export_format})"
```

## Current State

- App directory: `apps/reports/` — existe, mas vazio (sem arquivos Python)
- Relevant existing files: nenhum arquivo no app ainda
- BaseModel: `core/models.py` — já implementado
- URL include: `core/urls.py` já possui `path('', include('apps.reports.urls'))`
- Templates base: `templates/base.html`, `templates/includes/` existem
- Tests dir: `tests/__init__.py` existe
- Dependências: módulos Transactions, Categories e Cards devem estar implementados (consultas de dados)
- Patterns to follow: usar o padrão de service layer

## Tasks

### T1: Models — Criar modelo ScheduledReport
**What:** Criar o modelo `ScheduledReport` em `apps/reports/models.py` conforme Data Model acima. Criar `apps/reports/apps.py` com `ReportsConfig` (name=`apps.reports`). Criar `apps/reports/__init__.py`.
**Files:** `apps/reports/models.py`, `apps/reports/apps.py`, `apps/reports/__init__.py`
**Depends on:** none
**Verify:** `python manage.py makemigrations reports` gera a migration inicial sem erros

### T2: Migrations — Gerar e aplicar migration inicial
**What:** Gerar a migration inicial para o app reports e aplicar ao banco.
**Files:** `apps/reports/migrations/0001_initial.py`
**Depends on:** T1
**Verify:** `python manage.py migrate` executa sem erros; tabela `reports_scheduledreport` existe no banco

### T3: Selectors — Queries para dashboard e relatórios
**What:** Implementar selectors para consultas agregadas do dashboard:
- `get_dashboard_data(user, filters=None) -> dict` — retorna dados agregados: total_entradas, total_saidas, saldo, gastos_por_categoria (lista de {categoria, total}), evolucao_temporal (lista de {mes, entradas, saidas}), gastos_por_cartao (lista de {cartao, total}).
- `get_filtered_transactions(user, filters) -> QuerySet[Transaction]` — retorna transações filtradas para exportação. Filtros: period_start, period_end, category_ids, type, card_ids.
- `get_user_scheduled_reports(user) -> QuerySet[ScheduledReport]` — retorna relatórios agendados ativos do usuário.
**Files:** `apps/reports/selectors.py`
**Depends on:** T2, Transactions T2, Categories T2, Cards T2
**Verify:** Dashboard data retorna métricas corretas para transações de teste; filtros funcionam isoladamente e combinados

### T4: Service — Exportação de relatórios
**What:** Implementar serviços de exportação:
- `export_csv(transactions_queryset) -> HttpResponse` — gera arquivo CSV com cabeçalhos (nome, valor, tipo, categoria, cartão, data, status) e retorna como download.
- `export_xlsx(transactions_queryset) -> HttpResponse` — gera arquivo Excel com formatação usando `openpyxl`. Retorna como download.
- `export_pdf(transactions_queryset, user, filters) -> HttpResponse` — gera relatório PDF formatado usando `weasyprint`. Inclui resumo (totais) e tabela de transações. Retorna como download.
**Files:** `apps/reports/services.py`
**Depends on:** T3
**Verify:** Cada formato gera arquivo válido com dados corretos; arquivo é baixável via HttpResponse

### T5: Service — Agendamento de relatórios
**What:** Implementar serviços de agendamento:
- `create_scheduled_report(user, name, frequency, export_format, filters) -> ScheduledReport` — cria relatório agendado calculando `next_send_at` com base na frequência (semanal: +7 dias, quinzenal: +14 dias, mensal: +1 mês a partir de agora).
- `update_scheduled_report(report_id, user, **kwargs) -> ScheduledReport` — atualiza configuração. Recalcula `next_send_at` se frequência alterada.
- `deactivate_scheduled_report(report_id, user) -> ScheduledReport` — soft-delete.
- `process_due_reports()` — busca relatórios com `next_send_at <= agora` e `is_active=True`. Para cada: gera o arquivo no formato configurado, envia por e-mail como anexo, atualiza `last_sent_at` e calcula novo `next_send_at`.
**Files:** `apps/reports/services.py`
**Depends on:** T4
**Verify:** Relatório agendado criado com next_send_at correto; process_due_reports gera e envia relatório

### T6: Tasks — Celery task para relatórios agendados
**What:** Criar Celery task periódica que executa `process_due_reports()`:
- `send_scheduled_reports_task` — task registrada no Celery Beat, executada a cada hora. Chama `process_due_reports()` do service.
**Files:** `apps/reports/tasks.py`
**Depends on:** T5
**Verify:** Task é registrada no Celery Beat; execução processa relatórios pendentes

### T7: Views + URLs — Dashboard e endpoints
**What:** Implementar views:
- `DashboardView` (GET `/reports/`) — dashboard com gráficos e filtros. Template: `templates/reports/dashboard.html`. Passa dados do selector para o contexto.
- `ExportView` (GET `/reports/export/<format>/`) — exporta dados filtrados no formato solicitado (csv/xlsx/pdf). Retorna arquivo para download.
- `ScheduledReportListView` (GET `/reports/scheduled/`) — lista relatórios agendados. Template: `templates/reports/scheduled_list.html`
- `ScheduledReportCreateView` (GET/POST `/reports/scheduled/create/`) — formulário de criação. Template: `templates/reports/scheduled_form.html`. Redirect para list.
- `ScheduledReportDeleteView` (POST `/reports/scheduled/<uuid:pk>/delete/`) — soft-delete. Redirect para list.

Todas protegidas com `LoginRequiredMixin`. Configurar `apps/reports/urls.py` com `app_name = "reports"`.
**Files:** `apps/reports/views.py`, `apps/reports/urls.py`
**Depends on:** T3, T4, T5
**Verify:** `GET /reports/` retorna 200 com gráficos; export retorna arquivo válido; CRUD de agendamentos funciona

### T8: Templates — Dashboard e páginas de agendamento
**What:** Criar templates:
- `templates/reports/dashboard.html` — extends `base.html`. Seção de filtros (período, categoria, tipo, cartão). Área de métricas (cards com total entradas, saídas, saldo). Gráficos Chart.js: pizza (gastos por categoria), barra (evolução temporal), barra horizontal (gastos por cartão). Botões de exportação (CSV, Excel, PDF).
- `templates/reports/scheduled_list.html` — extends `base.html`. Lista de relatórios agendados com nome, frequência, formato, próximo envio. Botões de ação.
- `templates/reports/scheduled_form.html` — extends `base.html`. Formulário: nome, frequência, formato, filtros (período, categorias, tipo, cartões).
**Files:** `templates/reports/dashboard.html`, `templates/reports/scheduled_list.html`, `templates/reports/scheduled_form.html`
**Depends on:** T7
**Verify:** Dashboard renderiza gráficos Chart.js sem erros; filtros atualizam dados; formulário de agendamento funciona

### T9: Serializers — Serializers DRF para API
**What:** Criar serializers para a API:
- `DashboardSerializer` — campos: total_entradas, total_saidas, saldo, gastos_por_categoria (lista), evolucao_temporal (lista), gastos_por_cartao (lista). Read-only.
- `DashboardFilterSerializer` — campos: period_start, period_end, category_ids, type, card_ids. Para validação de query params.
- `ScheduledReportSerializer` — campos: id, name, frequency, export_format, filters, next_send_at, last_sent_at, created_at. Read-only.
- `ScheduledReportCreateUpdateSerializer` — campos: name, frequency, export_format, filters. Write.
**Files:** `apps/reports/serializers.py`
**Depends on:** T3, T5
**Verify:** Serializers validam dados corretamente; DashboardSerializer serializa dados agregados

### T10: API Views + URLs — Endpoints REST
**What:** Implementar API views com DRF:
- `DashboardAPIView` (GET `/api/v1/reports/dashboard/`) — retorna dados do dashboard com filtros via query params. Requer JWT.
- `ExportAPIView` (GET `/api/v1/reports/export/<format>/`) — retorna arquivo exportado (csv/xlsx/pdf) com filtros via query params. Requer JWT.
- `ScheduledReportListCreateAPIView` (GET/POST `/api/v1/reports/scheduled/`) — lista e cria relatórios agendados. Requer JWT.
- `ScheduledReportDetailAPIView` (GET/PUT/DELETE `/api/v1/reports/scheduled/<uuid:pk>/`) — detalhe, atualização e soft-delete. Requer JWT.

Todas com `permission_classes = [IsAuthenticated]`. Configurar `apps/reports/api_urls.py`. Incluir em `core/urls.py`: `path('api/v1/reports/', include('apps.reports.api_urls'))`.
**Files:** `apps/reports/api_views.py`, `apps/reports/api_urls.py`, `core/urls.py`
**Depends on:** T9
**Verify:** `GET /api/v1/reports/dashboard/` com JWT retorna dados; export retorna arquivo; CRUD de agendamentos via API funciona; sem JWT retorna 401

### T11: Admin — Registro no Django Admin
**What:** Registrar modelo `ScheduledReport` no Django Admin com:
- `list_display`: name, user, frequency, export_format, next_send_at, last_sent_at, is_active
- `list_filter`: frequency, export_format, is_active
- `search_fields`: name, user__email
- `readonly_fields`: id, created_at, updated_at, last_sent_at
**Files:** `apps/reports/admin.py`
**Depends on:** T2
**Verify:** `/admin/reports/scheduledreport/` lista registros; formulário funciona

### T12: Tests — Testes unitários e de integração
**What:** Implementar testes cobrindo:
- **Selectors:** dashboard data com transações de teste (totais, agrupamentos), filtros combinados, tenant isolation
- **Services (export):** CSV válido com cabeçalhos e dados, XLSX válido com openpyxl, PDF válido
- **Services (schedule):** criação com cálculo de next_send_at, process_due_reports envia e-mail com anexo e atualiza datas
- **Views (SSR):** dashboard autenticado, export retorna arquivo, CRUD de agendamentos
- **API:** GET dashboard com JWT e filtros, GET export retorna arquivo, CRUD scheduled reports via API, sem JWT → 401, tenant isolation via API
**Files:** `tests/reports/__init__.py`, `tests/reports/test_selectors.py`, `tests/reports/test_services.py`, `tests/reports/test_views.py`, `tests/reports/test_api.py`
**Depends on:** T8, T10, T11
**Verify:** `pytest tests/reports/` passa com 0 falhas

## Validation

**Happy path:**
1. Usuário acessa `/reports/` — dashboard exibe métricas zeradas (sem transações)
2. Após criar transações, dashboard mostra: total entradas, total saídas, saldo, gráfico de pizza por categoria, gráfico de barras por mês, gráfico por cartão
3. Usuário aplica filtro por período (último mês) → gráficos e métricas atualizam
4. Usuário clica em "Exportar CSV" → arquivo CSV é baixado com dados filtrados
5. Usuário clica em "Exportar Excel" → arquivo .xlsx é baixado
6. Usuário clica em "Exportar PDF" → relatório PDF formatado é baixado
7. Usuário agenda relatório semanal em PDF → aparece na lista de agendamentos com próxima data de envio
8. Task Celery executa → e-mail com PDF anexo é enviado; próxima data é recalculada

**Edge cases:**
- Dashboard sem transações → métricas zeradas, gráficos vazios com mensagem informativa
- Exportação com filtros que retornam 0 resultados → arquivo gerado com cabeçalhos mas sem dados
- Relatório agendado de usuário desativado → task ignora (is_active=False)
- Filtros com período inválido (data fim antes de data início) → erro de validação
- Usuário A não vê relatórios agendados do Usuário B → tenant isolation

**Commands:**
```bash
pytest tests/reports/
# Manual: acessar /reports/ e verificar gráficos com dados de teste
# Manual: exportar cada formato e validar conteúdo do arquivo
# Manual: criar agendamento e verificar no Django Admin
```
