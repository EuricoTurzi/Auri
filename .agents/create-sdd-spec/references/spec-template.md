# [Module Name]

## Why

[1-2 sentences: what problem this module solves and why it matters in this system.]

## What

[Concrete deliverable. Specific enough that an agent can verify when it is done.
Example: "Backoffice can create a Customer with an admin user. The user receives
a one-time password by email and must change it on first login."]

## Decisions

[Technical decisions extracted from the source document. One per line.]

- Auth strategy: [e.g., Session Auth — Django Templates, no SPA]
- Backoffice access: [e.g., Django Admin]
- [Other explicit decisions...]

> Assumption: [Any decision inferred but not stated in the source, with reason.]

## Constraints

### Must
- [Required patterns, libraries, or conventions — be specific]
- All models inherit BaseModel (UUID pk, created_at, updated_at, is_active)
- Soft-delete via `is_active=False` — never use hard DELETE on these models
- Tenant isolation: every queryset on tenant-scoped models must filter by `request.user.tenant`

### Must Not
- [Forbidden approaches]
- No new dependencies without listing them here
- Do not modify files outside this module's `apps/<name>/` scope

### Out of Scope
- [Adjacent features explicitly not being built in this spec]

## Data Model

[Full field definitions in Django syntax. One block per model.]

```python
# BaseModel (abstract) — all models below inherit this
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

# [ModelName] — [one-line purpose]
class ModelName(BaseModel):
    field_name = models.FieldType(options)
    # FK example:
    tenant = models.ForeignKey("Customer", on_delete=models.PROTECT, related_name="users")
    # Choices example:
    ROLE_CHOICES = [("admin", "Admin"), ("operador", "Operador")]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
```

## Current State

[What already exists. Saves the implementing agent from exploring.]

- App directory: `apps/<name>/` — [exists / to be created]
- Relevant existing files: [list or "none yet"]
- Patterns to follow: [e.g., see `apps/accounts/services.py` for service pattern]

## Tasks

<!-- Layer order: Models → Migrations → Services → Selectors → Views/URLs → Templates → Admin → Tests -->
<!-- Each task = one layer concern. Max 3 files. -->

### T1: [Models]
**What:** [Exact description of what to implement, referencing field names from Data Model above]
**Files:** `apps/<name>/models.py`, `apps/<name>/apps.py`
**Depends on:** none
**Verify:** `python manage.py makemigrations --check` exits 0 (or creates migration if first run)

### T2: [Migrations]
**What:** Generate and apply the initial migration for this app.
**Files:** `apps/<name>/migrations/0001_initial.py`
**Depends on:** T1
**Verify:** `python manage.py migrate` runs without errors; table exists in DB

### T3: [Service — description]
**What:** [Which function(s) to write, inputs, outputs, and side effects.
  Example: `create_customer(cnpj, nome_fantasia, email_contato) -> Customer`
  Creates Customer + admin CustomUser with random password, sends email.]
**Files:** `apps/<name>/services.py`, `tests/<name>/test_services.py`
**Depends on:** T2
**Verify:** Unit test calls the service with valid data and asserts [expected outcome]

### T4: [Selector — description] *(omit if no complex read queries)*
**What:** [Which selector function(s) to write and their query logic]
**Files:** `apps/<name>/selectors.py`, `tests/<name>/test_selectors.py`
**Depends on:** T2
**Verify:** Selector returns only records belonging to the correct tenant

### T5: [Middleware or Mixin — description] *(omit if not applicable)*
**What:** [Auth gate, tenant filter, or first-access redirect logic]
**Files:** `apps/<name>/mixins.py` (or `middleware.py`)
**Depends on:** T3
**Verify:** [Specific behavior test — e.g., user with must_change_password=True is redirected]

### T6: [Views + URLs — description]
**What:** [Which views, which HTTP methods, which template each view renders]
**Files:** `apps/<name>/views.py`, `apps/<name>/urls.py`, `core/urls.py`
**Depends on:** T3, T5
**Verify:** `GET /path/` returns 200; `POST /path/` with valid data redirects to [destination]

### T7: [Templates — description]
**What:** [Which templates to create and what each one must contain]
**Files:** `templates/<name>/<page>.html`, `templates/partials/<component>.html`
**Depends on:** T6
**Verify:** Page renders without template errors; form submits correctly

### T8: [Admin — description]
**What:** Register [ModelName] in Django Admin with [list/search/filter fields]
**Files:** `apps/<name>/admin.py`
**Depends on:** T2
**Verify:** `/admin/<name>/` lists records; create form works end-to-end

### T9: [Tests — integration]
**What:** Integration tests covering the full flow described in Validation below
**Files:** `tests/<name>/test_flows.py`
**Depends on:** T6, T7, T8
**Verify:** `python manage.py test tests/<name>/` passes with 0 failures

## Validation

[End-to-end scenario covering the full happy path and key edge cases.]

**Happy path:**
1. [Step 1 — actor + action + expected result]
2. [Step 2...]

**Edge cases:**
- [Edge case 1 — what happens and how the system responds]
- [Edge case 2...]

**Commands:**
```bash
python manage.py test tests/<name>/
# Manual check: [what to verify in browser/admin]
```
