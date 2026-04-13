# GEMINI.md

Este arquivo fornece orientação ao agente **Gemini** ao trabalhar neste repositório.

## Escopo do Agente

O Gemini é um agente **dedicado exclusivamente ao frontend** do projeto Auri. Sua atuação é limitada a:

- Templates Django (`templates/` e `apps/*/templates/`)
- Estilos (`static/styles/` e qualquer CSS do projeto)
- JavaScript do cliente (vanilla JS nos templates e em `static/`)
- Assets estáticos (imagens, ícones, fontes locais)

**Proibido tocar em:** `models.py`, `views.py`, `services.py`, `urls.py` (exceto rotas de templates estáticos), `settings/*.py`, migrations, `forms.py`, `serializers.py`, `admin.py`, `requirements.txt`, configurações de Docker ou CI. Se uma mudança visual exigir alteração em backend (novo contexto em view, novo campo em model, nova rota), **pare e delegue** ao usuário ou ao Claude.

## Visão Geral do Projeto

**Auri** é uma aplicação Django para controle de finanças pessoais. A UI é **SSR via Django Templates** (sem SPA, sem React/Vue/Next). Estética "dark luxury / private banking" — fundo escuro, acentos dourados, tipografia serif para marca e sans para corpo.

Domínios funcionais que o frontend representa:
- **accounts** — autenticação, registro, login
- **transactions** — registro de entradas/saídas, recorrências, parcelamentos
- **cards** — controle de cartões do usuário
- **categories** — tags configuráveis
- **reports** — exportação em Excel, CSV, PDF
- **assistant** — interface de IA para registro por áudio/linguagem neutra

## Ambiente de Desenvolvimento

- **SO:** Windows, terminal Git Bash. Use sintaxe Unix (`/dev/null`, barras normais).
- **Diretório restrito:** trabalhe exclusivamente dentro de `D:\Development\Auri`. Não execute comandos que afetem o SO (registry, services, pacotes globais).
- **Virtualenv:** `source venv/Scripts/activate` antes de qualquer comando Python.

### Comandos úteis

```bash
# Ativar o venv
source venv/Scripts/activate

# Subir o servidor (para validação visual)
export DJANGO_SETTINGS_MODULE=core.settings.development
python manage.py runserver

# Coletar estáticos quando necessário
python manage.py collectstatic --noinput
```

## Stack Frontend

| Camada          | Ferramenta                                               |
| --------------- | -------------------------------------------------------- |
| CSS framework   | **Tailwind CSS v3** via CDN (`cdn.tailwindcss.com`)      |
| CSS custom      | `static/styles/main.css` (glass morphism, gradientes)    |
| Animações       | **GSAP 3.14.2 + ScrollTrigger** via CDN                  |
| JavaScript      | **Vanilla JS** — sem Alpine, HTMX, React, Vue            |
| Fontes          | Google Fonts — **Outfit** (sans) + **Playfair Display** (serif) |
| Build tooling   | **Nenhum** — sem Webpack, Vite, package.json             |

### Configuração Tailwind custom

A configuração vive inline em `templates/base.html` (linhas 17–60). Ela estende o Tailwind com:

**Paleta de cores:**
- `dark`: `950=#08070d`, `900=#0e0d15`, `800=#16141f`, `700=#1e1c28`, `600=#272432`
- `gold`: `50..900` (tom principal de acento = `gold-400=#d4b85c`)
- `emerald`: `400=#4ade80`, `500=#22c55e`

**Tipografia:**
- `font-sans` → Outfit
- `font-serif` → Playfair Display

**Extras:**
- `rounded-4xl` (2rem), `rounded-5xl` (2.5rem)
- `tracking-widest-plus` (0.2em)

Sempre que precisar de uma cor/token novo, primeiro verifique se já existe nessa config. Se não existir e for reutilizável, adicione à config em `base.html` ao invés de hardcode inline.

## Estrutura de Templates

```
templates/
  base.html                  ← Layout global (navbar pill + footer + blocks)
  landing.html               ← Referência de design (GSAP, hero, sections)
  includes/
    navbar.html              ← Navbar pill flutuante (vanilla JS de scroll)
    sidebar.html
  errors/
    403.html / 404.html / 500.html
  <app>/                     ← Templates por app (transactions/, accounts/, etc.)
```

### Blocks disponíveis em `base.html`

- `{% block title %}` — título da aba
- `{% block meta_description %}` — meta description
- `{% block extra_head %}` — CSS/JS adicional no `<head>`
- `{% block navbar %}` — sobrescrever navbar se necessário
- `{% block content %}` — conteúdo principal
- `{% block footer %}` — sobrescrever footer
- `{% block extra_scripts %}` — scripts no final do `<body>`

**Sempre estenda `base.html`.** Use `{% load static %}` + `{% static 'styles/...' %}` para referenciar assets.

## Design System (flexível)

A base é **dark luxury**, mas há liberdade criativa para experimentar padrões novos desde que coerentes com o conjunto.

### Guidelines base

- **Background:** `bg-dark-950`, texto `text-white` com opacidades (`text-white/25`, `/40`, `/50`, `/70`) para hierarquia.
- **Acentos:** `text-gold-400`, `border-gold-500/20`, gradientes gold em CTAs.
- **Tipografia:** `font-serif` para marca e títulos nobres, `font-sans` para corpo, `tracking-widest-plus` + `uppercase` + `text-[10px]` para labels discretos.
- **Espaçamento:** generoso. Prefira `py-16`, `py-20`, `gap-10+` em seções.
- **Bordas:** suaves — `rounded-4xl`, `rounded-5xl`, `border-white/[0.04]`.
- **Glass morphism:** recurso recorrente — usar classes custom de `main.css` (`.card-surface`, `.divider-gold`, etc.).
- **Animações:** GSAP para entradas de seção e parallax. Veja `landing.html` para padrões canônicos.

### Liberdade criativa

Os arquivos `templates/landing.html` e `static/styles/main.css` são o **norte visual**, não uma camisa de força. Você pode:
- Experimentar novas variações de layout
- Introduzir novos componentes coerentes com a estética
- Estender `main.css` com novas classes utilitárias custom
- Propor refinamentos tipográficos ou de espaçamento

Se a experimentação se afastar muito da base, descreva a decisão brevemente na mensagem de commit.

## MCPs disponíveis

### Playwright MCP (obrigatório para validação visual)

Use estas tools para validar qualquer mudança de UI:

- `browser_navigate` — abrir uma rota
- `browser_snapshot` — snapshot acessível do DOM
- `browser_take_screenshot` — screenshot visual
- `browser_resize` — testar viewports (mobile ~390px, tablet ~768px, desktop ~1440px)
- `browser_click`, `browser_type`, `browser_fill_form` — interações
- `browser_console_messages` — checar erros JS
- `browser_network_requests` — conferir requisições e 404 em assets

### Context7 (ou equivalente de documentação)

Consulte sempre que precisar de referência de API **antes de inventar**:
- Tailwind CSS (classes utilitárias, variantes, config)
- GSAP (timelines, ScrollTrigger, easing)
- APIs DOM modernas

## Workflow

### Commits agrupados

Agrupe mudanças coesas em **um único commit descritivo**, não commit por micro-task. Exemplos de unidades coesas:
- "Nova página de dashboard de transações completa"
- "Refatoração da navbar + menu mobile"
- "Ajustes de responsividade da landing"

Padrão da mensagem (em **português**):
- `feat(ui): nova página de listagem de transações`
- `style(navbar): ajusta glass morphism e breakpoint mobile`
- `fix(landing): corrige overflow do hero em telas pequenas`
- `refactor(templates): extrai footer para include`

**Nunca** use `--no-verify`, force push, ou `reset --hard` em branches compartilhadas. Se um hook falhar, investigue e conserte.

## Validação obrigatória (Playwright)

**Toda** mudança visual precisa passar por validação no browser antes de ser reportada como concluída. Fluxo mínimo:

1. **Garantir servidor rodando** — `python manage.py runserver` em background (ou confirmar que já está ativo).
2. **Navegar** — `browser_navigate` para a(s) rota(s) afetada(s).
3. **Capturar** — `browser_take_screenshot` em pelo menos dois viewports:
   - Desktop (`browser_resize` para ~1440×900)
   - Mobile (`browser_resize` para ~390×844)
4. **Checar console** — `browser_console_messages` precisa estar limpo (sem erros JS, sem 404 de assets).
5. **Validar interações-chave** — se houver menu mobile, modal, dropdown, testar o clique.
6. **Reportar** — só então declare a mudança concluída, mencionando o que foi verificado.

Se não conseguir subir o servidor ou usar o Playwright, **declare explicitamente** ("não consegui validar visualmente porque X") em vez de afirmar que está funcionando.

## Restrições de Segurança

- **Permitido:** editar HTML/CSS/JS dentro de `templates/` e `static/`, rodar `manage.py runserver`/`collectstatic`, git, Playwright MCP.
- **Proibido:** instalar pacotes do sistema, alterar env vars globais, tocar em arquivos Python de backend (models/views/services/urls/settings/migrations/forms/serializers), editar `requirements.txt`, mexer em Docker/CI, acessar diretórios fora de `D:\Development\Auri`.
- **Em dúvida:** pergunte ao usuário antes de agir.

## Idioma

Todo código, comentário, template, mensagem de commit e documentação em **português (pt-br)**.
