# Auri

**Sistema de controle financeiro pessoal — modular, sob medida e com assistente de IA para registro por áudio.**

---

## Sobre

O **Auri** é um sistema de controle financeiro pessoal construído sob medida. O mercado já tem dezenas de apps de finanças, mas nada supera um sistema modular, adaptado ao fluxo de quem o usa e extensível conforme a necessidade.

Entre os diferenciais está um módulo integrado de **Inteligência Artificial** que permite registrar transações por captura de áudio, em linguagem natural — não é preciso ser especialista para utilizar.

## Funcionalidades

O sistema é dividido em módulos com isolamento de domínio:

- **Accounts** — autenticação por login/senha, registro com envio de senha de primeiro acesso por e-mail, troca obrigatória no primeiro login. OAuth Google planejado.
- **Transactions** — núcleo do sistema. Entradas e saídas, com suporte a recorrência, parcelamento, categorização, nomenclatura e descrição.
- **Cards** — cadastro e controle de gastos em cartões do usuário.
- **Categories** — categorização via tags configuráveis pelo próprio usuário, sem categorias hardcoded.
- **Reports** — extração de relatórios em CSV, Excel e PDF.
- **Assistant** — interface de IA que transcreve áudio e registra transações em linguagem neutra.

## Stack técnica

- **Backend:** Python + Django (monolito modular, SSR via Django Templates no MVP)
- **API:** Django REST Framework — estruturada desde o início para futura integração com Next.js e mobile
- **Banco de dados:** PostgreSQL 16 (Docker em desenvolvimento, AWS RDS em produção)
- **Testes:** pytest + pytest-django, abordagem TDD orientada por specs
- **Convenções de modelagem:** primary keys UUID, `BaseModel` com `created_at` / `updated_at` / `is_active`, soft-delete como padrão

## Estrutura do projeto

```text
Auri/
├── apps/
│   ├── accounts/         # Autenticação e CustomUser
│   ├── transactions/     # Core — entradas, saídas, recorrências, parcelas
│   ├── cards/            # Cartões do usuário
│   ├── categories/       # Tags/categorias configuráveis
│   ├── reports/          # Exportação CSV / Excel / PDF
│   └── assistant/        # Assistente IA (áudio → transação)
├── core/
│   └── settings/
│       ├── base.py
│       ├── development.py
│       └── production.py
├── templates/            # Django Templates (SSR)
├── static/
├── specs/                # Specs SDD por módulo
├── .docs/                # Documentação técnica e de módulos
├── tests/
├── docker-compose.yml    # Postgres local
├── requirements.txt
└── manage.py
```

## Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- Git

## Setup local

```bash
# 1. Clonar o repositório
git clone <url-do-repo> Auri
cd Auri

# 2. Criar virtualenv e instalar dependências
python -m venv .venv
source .venv/Scripts/activate   # Git Bash no Windows
pip install -r requirements.txt

# 3. Subir o Postgres (porta 5434 no host)
docker-compose up -d

# 4. Configurar settings de desenvolvimento
export DJANGO_SETTINGS_MODULE=core.settings.development

# 5. Rodar migrações
python manage.py migrate

# 6. Criar superusuário (opcional)
python manage.py createsuperuser

# 7. Rodar o servidor de desenvolvimento
python manage.py runserver
```

A aplicação ficará disponível em `http://localhost:8000`.

## Testes

O projeto segue **TDD** — testes são escritos antes da implementação, guiados pelas specs em `specs/`.

```bash
# Rodar toda a suíte
pytest

# Rodar um teste específico
pytest -k "test_name"
```

A cobertura foca em regras de negócio (camada de *services* / *managers*) e contratos de view (template correto + contexto correto).

## Roadmap

1. **MVP** — SSR completo com Django Templates
2. **APIs REST** — DRF estruturado desde o início do MVP
3. **Frontend SPA (Next.js)** — duas semanas após o lançamento do MVP
4. **Mobile** — dois meses após a entrega do frontend Next.js

## Documentação

- [`.docs/documentation.md`](.docs/documentation.md) — arquitetura global e padrões técnicos
- `.docs/modules/<módulo>.md` — documentação funcional por módulo
- `specs/<módulo>/spec.md` — especificações técnicas SDD
- [`CLAUDE.md`](CLAUDE.md) — orientações para agentes de desenvolvimento

Toda a documentação e os comentários de código são mantidos em **português (pt-br)**.

## Autor

Projeto pessoal mantido por **Eurico**.
