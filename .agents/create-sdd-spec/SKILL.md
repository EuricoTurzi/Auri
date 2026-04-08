---
name: create-sdd-spec
description: Create standardized SDD feature specs from repository source docs. Use when Codex needs to turn a feature brief from `.docs/` (or `.doc/` if the repo uses that variant) into a detailed `specs/<feature-name>/spec.md`, while reviewing the request for clarity, preserving context, and checking for similar existing specs before creating a new one.
---

# Create SDD Spec

Create a complete, implementation-ready feature spec from a repository document. The output must be precise enough that an AI agent can execute each task in a fresh session without asking clarifying questions.

## Core Principle

The spec is an action plan for agents, not a PRD for stakeholders. Every section must reduce guesswork — if a section can be misinterpreted, it is not done.

## Gather Input

Resolve the source document from one of these inputs:

- an explicit path
- a feature name that maps to `.docs/modules/<name>` or `.docs/modules/<name>.md`
- a legacy path under `.doc/`

If multiple matches exist, choose the closest exact match and list the alternatives in the final report.

## Follow Workflow

1. Read the source document completely before drafting anything.
2. Check for similar specs in `specs/` — if a conflict is found, stop and surface the existing path instead of creating a duplicate.
3. Review the source document for ambiguity, missing constraints, conflicting requirements, and missing validation details.
4. Resolve every gap: turn implied rules into explicit constraints, or add a clearly marked `> Assumption:` block.
5. Inspect the minimum repository context needed to write accurate file paths in `Current State` and `Tasks`.
6. Write the completed spec to `specs/<slug>/spec.md` using [references/spec-template.md](references/spec-template.md).

## Django-Specific Extraction Rules

This project is a Django monolith using the service-layer pattern. When reading the source document, extract and map content to the correct Django layer:

| Source content | Spec section | Django layer |
|---|---|---|
| Model fields, BaseModel, soft-delete, UUIDs | `Data Model` | `models.py` |
| Business rules, workflows, computed logic | Tasks → `services.py` | Service layer |
| Read queries, filtered lists, complex ORM | Tasks → `selectors.py` | Selector layer |
| HTTP endpoints, form handling, redirects | Tasks → `views.py` + `urls.py` | View layer |
| Auth checks, tenant isolation, first-access gate | Tasks → `middleware.py` or mixins | Middleware/Mixin |
| HTML pages and forms | Tasks → `templates/<app>/` | Template layer |
| Reusable partial components | Tasks → `templates/partials/` | Template partials |
| Django Admin registration | Tasks → `admin.py` | Admin layer |
| Test coverage | Tasks → `tests/<app>/` | Test layer |
| Signals, async tasks | Tasks → `signals.py` / `tasks.py` | Event/Task layer |
| DB schema changes | Every model task must include migration step | `makemigrations` |

## Task Design Rules

- Design tasks for fresh sessions — each task must make sense with only the spec as context.
- One task = one Django layer concern. Do not mix model + service + view in a single task.
- Maximum 3 files per task. If it touches more, split it.
- Every task must have a `**Depends on:**` line (or `none`) and a concrete `**Verify:**` step.
- Task sequence must respect layer order: Models → Migrations → Services → Selectors → Views/URLs → Templates → Admin → Tests.
- Prefer a sequence that supports `Spec → Task → Review → Commit`.
- Authentication and tenant isolation tasks must come before any view task that requires them.

## Data Model Section Rules

For every model in the source document, the spec must include:

- Exact field names, types, and options (null, blank, default, unique, choices)
- Which models inherit BaseModel
- FK targets and `on_delete` behavior
- `choices` as explicit tuples when the source mentions enums/roles/flags
- Whether soft-delete applies (`is_active`) or hard-delete
- Index hints if any field is used for frequent filtering

## Decisions Section Rules

If the source document explicitly states a technical decision (auth method, library, pattern), record it in `## Decisions` with its reason. If a decision is implied but not stated, add it as:

> Assumption: [decision]. Reason: [why this was inferred].

Never leave a decision implicit in the `Tasks` section alone.

## Review Checklist

Before writing the final spec, confirm every item is answered or explicitly assumed:

- [ ] Business problem and motivation
- [ ] Concrete deliverable (verifiable when done)
- [ ] Auth strategy (Session / JWT / None)
- [ ] Tenant isolation strategy (how queryset filtering works)
- [ ] All models with full field definitions
- [ ] All service functions with input/output described
- [ ] All URL patterns and their view names
- [ ] Template names and which views render them
- [ ] Django Admin registration (yes/no, which models)
- [ ] Migration steps per model task
- [ ] Test coverage targets per task
- [ ] End-to-end validation scenario

If any item is missing from the source, add an explicit `> Assumption:` block in the relevant spec section.

## Output Rules

- Write the spec to `specs/<slug>/spec.md`.
- Keep the heading format and section order from the reference template.
- Use exact repository file paths (e.g., `apps/accounts/services.py`, not `services.py`).
- Do not create extra planning files unless the user asks for them.
- All field definitions must use Python/Django syntax, not prose.

## Report Outcome

After writing the spec, report:

- Source document used
- Output path
- Any similar specs found
- Key assumptions added during review
- Decisions extracted from source vs. assumptions inferred
