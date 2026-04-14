# CLAUDE.md

Este arquivo fornece orientação ao Claude Code (claude.ai/code) ao trabalhar com código neste repositório.

# **IMPORTANTE**

- Os itens **# Anotações**, **# Workflow de Implementação** e **Obsidian** devem ser seguidos OBRIGATÓRIAMENTE. A cada task, deve ser commitado e ao final da implementação da spec, o napkin deve ser atualizado. Antes de qualquer atualização, verifique o arquivo `C:\Users\eurico.dante\Desktop\Development\Auri\.claude\napkin.md`

## Anotações

- **Todas** as anotações devem utilizar a skill Napkin para registrar mudanças e registros de tasks realizadas.
- O caminho da skill é: `"C:\Users\eurico.dante\.claude\plugins\data\napkin-main"`
- **Sempre** checar as anotações do napkin

## Workflow de Implementação

- **Commit por task:** ao finalizar cada task de uma spec, criar um commit dedicado com mensagem descritiva (ex: `feat(accounts): T1 — CustomUser model e manager`). Não acumular múltiplas tasks em um único commit. 

# Obsidian

Estou implementando o Obsidian junto aos meus projetos, siga as regras abaixo para controle total.
Caso alguma pasta não tenha sido criada ainda, crie dentro do Obsidian.

Este projeto mantém documentação de design e specs no vault Obsidian em `Auri/`.
Use o MCP do Obsidian [obisidian-mcp-tools] para:
- Atualizar notas de specs dos módulos após implementar mudanças
- Consultar decisões arquiteturais em `Auri/architecture/`
- Sincronizar status de implementação em `Auri/modules/<modulo>/status.md`

### Ao concluir uma feature, atualize a nota correspondente no Obsidian com:
- Data da implementação
- Decisões tomadas que divergiram da spec
- Testes adicionados

### Implementação de features:
O Obsidian possui uma pasta para registros de features, `Auri/features`, nele contém notas com funcionalidades que precisam ser inseridas no sistema. Eu utilizo a divisão de feature por módulo, `Auri/features/<module>/feature-name.md`.
- Leia as notas e identifique as funcionalidades.
- Crie um plano de implementação seguindo o padrão de SDD com TDD.
- Não execute o plano até que tenha o meu OK e revisão.
- Em alterações diretas em templates, não faça a execução, registre o que deve ser alterado na pasta `Auri/frontend/<module>/feature-name.md`.
- Após executado a feature, registrar flag no nome do arquivo.

### Tratamento de erros:
O obisidian possui uma pasta para erros reportados, `Auri/errors` nele contem notas de erros utilizando a seguinte nomenclatura `erro-numero_do_erro-data_do_registro`.
- Leia as notas e identifique os erros.
- Planeje a solução com base nos erros identificados
- Atualize as notas informando o que foi alterado, fica em `Auri/solutions`
- Renomeie a nota do erro com o id do erro para concluido.

## Visão Geral do Projeto

**Auri** é uma aplicação Django para controle de finanças pessoais. Sistema modular com registro de transações, categorização, controle de cartões, relatórios e um assistente integrado com IA para registro por áudio/linguagem neutra.

## Ambiente de Desenvolvimento

- **SO:** Windows. O terminal roda no Git Bash.
- **Restrições de acesso:** Acesso restrito exclusivamente ao diretório do projeto e ferramentas de desenvolvimento. Não executar comandos que afetem o sistema operacional (registry, services pacotes do sistema). Limitar-se a operações de código, git, pip, pytest, Django e Docker.

## Comandos de Desenvolvimento

```bash
# Selecionar ambiente de settings
export DJANGO_SETTINGS_MODULE=core.settings.development

# Rodar servidor de desenvolvimento
python manage.py runserver

# Rodar migrações
python manage.py migrate

# Rodar testes (TDD — sempre escrever testes primeiro)
pytest
pytest -k "test_name"                           # Rodar um teste específico

# Coletar arquivos estáticos
python manage.py collectstatic

# Instalar dependências (usar pip, não uv)
pip install -r requirements.txt
```

## Arquitetura

### Monolito Modular Django (SSR only — MVP)

- **Sem frameworks SPA** — Django Templates exclusivamente para toda UI no MVP. Sem React, Vue ou Angular nesta etapa.
- APIs REST serão estruturadas desde o início (DRF) para futura integração com frontend SPA (Next.js) e mobile, mas não serão consumidas no MVP.
- Comunicação entre apps ocorre pela **camada de services** (`services.py`) ou Django Signals — nunca importação direta de models entre apps.
- Cada app vive em `apps/<domínio>/`.

### Apps

| App             | Responsabilidade                                                              |
| --------------- | ----------------------------------------------------------------------------- |
| `accounts`      | Autenticação (login/senha), CustomUser, registro com e-mail de primeiro acesso |
| `transactions`  | Core do sistema — registro de entradas/saídas, recorrências e parcelamentos   |
| `cards`         | Controle de cartões cadastrados pelo usuário                                  |
| `categories`    | Categorização de transações — tags configuráveis por usuário                  |
| `reports`       | Extração de relatórios (Excel, CSV, PDF)                                      |
| `assistant`     | Interface de IA para registro de transações por áudio/linguagem neutra        |

### Convenções de Data Model

- Todas as primary keys são **UUID** (sem auto-increment IDs).
- Todos os models importantes herdam de `BaseModel` com `id`, `created_at`, `updated_at`, `is_active`.
- **Soft-delete** (`is_active=False`) é o padrão para registros sensíveis. Hard-delete apenas para logs e tabelas pivô simples.

### Separação de Settings

- `core/settings/base.py` — configuração compartilhada
- `core/settings/development.py` — DEBUG=True, Celery eager, console email
- `core/settings/production.py` — SSL/HTTPS enforced, SMTP email, file logging em `logs/django.log`

### Serviços Externos

- **PostgreSQL** — banco principal (Docker em dev, AWS RDS em prod)

## Frontend Design System

Utilizar o arquivo de landing-page como referencia e a skill frontend-design
Utilizar a skill taste-skill para auxiliar no design-pattern do frontend: https://github.com/Leonxlnx/taste-skill/

### Estrutura de Templates

```
templates/
  base.html                  ← Base landing/auth (navbar pill modo landing)
  includes/
    navbar.html              ← Navbar pill flutuante
    sidebar.html
  errors/
    403.html / 404.html / 500.html
  <app>/                     ← Templates por app (ex: transactions/, accounts/)
```

## Documentação

- `.docs/documentation.md` — arquitetura global e padrões técnicos
- `.docs/modules/<módulo>.md` — documentação de funcionalidades por módulo
- `specs/<módulo>/spec.md` — especificações técnicas SDD (blueprint de implementação, em revisão)

Toda documentação e comentários de código em **Português (pt-br)**.

## Regras de Segurança para Agentes

- **Proibido:** comandos que alterem configurações do SO, instalem pacotes de sistema, modifiquem variáveis de ambiente globais ou acessem diretórios fora do projeto.
- **Permitido:** operações dentro do diretório do projeto — git, pip (virtualenv), pytest, Django management commands, Docker Compose, leitura/escrita de arquivos do projeto.
- Agentes paralelos devem operar exclusivamente no escopo do código-fonte e ferramentas de desenvolvimento.
