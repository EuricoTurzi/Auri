# Reports

## Entrega Esperada

O módulo `Reports` é responsável pela visualização de dados financeiros em dashboard e pela exportação de relatórios. Combina um painel visual com gráficos e a possibilidade de extração de dados nos formatos CSV, Excel e PDF.
O módulo também permite agendamento de relatórios periódicos, enviados automaticamente por e-mail.

## Regras de Negócio

`Relatórios e dashboards exibem exclusivamente dados do usuário autenticado.`

### Dashboard

- O dashboard apresenta visão consolidada das finanças do usuário com gráficos interativos.
- Métricas esperadas:
    - Total de entradas e saídas no período.
    - Saldo (entradas - saídas).
    - Distribuição de gastos por categoria.
    - Evolução de gastos ao longo do tempo.
    - Gastos por cartão.

### Filtros

- Todos os relatórios e visualizações aceitam os seguintes filtros:
    - **Período**: intervalo de datas (data início e data fim).
    - **Categoria**: uma ou mais categorias.
    - **Tipo**: entrada, saída ou ambos.
    - **Cartão**: um ou mais cartões.

### Exportação

- O usuário pode exportar os dados filtrados nos seguintes formatos:
    - **CSV**: dados tabulares simples.
    - **Excel (.xlsx)**: dados formatados em planilha.
    - **PDF**: relatório formatado para impressão/compartilhamento.
- A exportação respeita os filtros aplicados no momento da extração.

### Agendamento de Relatórios

- O usuário pode agendar o envio automático de relatórios por e-mail.
- Frequências disponíveis: **semanal**, **quinzenal** ou **mensal**.
- O relatório agendado é gerado com base nos filtros configurados pelo usuário no momento do agendamento.
- O relatório é enviado no formato escolhido pelo usuário (CSV, Excel ou PDF) como anexo do e-mail.

`Para auditoria, agendamentos devem herdar o BaseModel contido em core/models.py`

## Modelo de Dados

- ScheduledReport (Herda de BaseModel):
    - user: ForeignKey → CustomUser
    - name: CharField
    - frequency: CharField (choices: semanal, quinzenal, mensal)
    - export_format: CharField (choices: csv, xlsx, pdf)
    - filters: JSONField (armazena os filtros configurados)
    - last_sent_at: DateTimeField (null=True, blank=True)
    - next_send_at: DateTimeField

## Fluxo de Exportação Manual

- Usuário aplica os filtros desejados no dashboard.
- Usuário seleciona o formato de exportação (CSV, Excel ou PDF).
- Service consulta as transações do usuário com os filtros aplicados.
- Service gera o arquivo no formato solicitado.
- Retorna o arquivo para download.

## Fluxo de Agendamento de Relatório

- Usuário configura os filtros e seleciona a frequência e formato desejado.
- Serializer valida os filtros e campos obrigatórios.
- Service cria o ScheduledReport com o cálculo do próximo envio (next_send_at).
- Uma task periódica (Celery/Cron) verifica os relatórios com `next_send_at <= agora`.
- Para cada relatório pendente, a task gera o arquivo e dispara o e-mail com o anexo.
- Atualiza `last_sent_at` e calcula o próximo `next_send_at`.
