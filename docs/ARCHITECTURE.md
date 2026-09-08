# Northstar HRMS — Architecture

This document describes the current implementation: what runs, how the pieces fit, how multi-tenancy and authorization are enforced, and where each concern lives.

## 1. System overview

```
Browser (Vue 3 SPA)
   │  REST /api/*   (JWT Bearer)
   ▼
FastAPI app (app.main:create_app)
   │  SQLAlchemy session per request
   ▼
SQLite (default ./data/ats.db)   +  optional SMTP / Google Calendar / LLM API
```

The frontend is a single Vue app served by Vite. In development it proxies `/api` to the FastAPI backend (`frontend/vite.config.ts`). There is no separate auth service; JWT is issued by the backend and validated per request.

## 2. Backend layout

- `app/main.py` — FastAPI app factory, CORS, router registration, lifespan that creates tables and runs additive SQLite migrations (`db.migrate_sqlite`).
- `app/config.py` — pydantic-settings; enforces `JWT_SECRET` (≥32 chars) and `DATA_ENCRYPTION_KEY` on startup.
- `app/db.py` — engine/session factory (`make_engine`, `init_engine`, `get_db`), static pool for `:memory:` test DBs, lightweight migration helper.
- `app/models.py` — every SQLAlchemy model for every module in one file (see §5).
- `app/crypto.py` — Fernet encryption for PII fields (`email_enc`, `name_enc`, `phone_enc`) and HMAC-SHA256 email hash used for uniqueness and lookup.
- `app/deps.py` — shared auth dependencies.
- `app/errors.py` — `conflict()` helper returning structured 409 payloads.
- `app/themes.py` — theme/layout/module catalog + org serialization.
- `app/modules/*` — one package per feature area, each exposing a FastAPI `router`. Feature logic sits in module `router.py` (API layer) plus small `service.py` files where flows are reused (auth, jobs, candidates, mail, calendar, screening).

## 3. Authentication & RBAC

- Flow: `POST /api/auth/register` or `/login` returns `{token, user}`. The token is a signed HS256 JWT containing `sub` (user id) and `role`. The frontend stores it in `localStorage` (`ats_token`) and sends `Authorization: Bearer …`.
- `get_current_user` (app/deps.py) decodes the JWT, loads the user, rejects deleted/unknown accounts.
- Role dependencies, all in `app/deps.py`:

| Dependency | Allowed roles | Typical use |
| --- | --- | --- |
| `get_current_user` | any authenticated | "my own data" endpoints |
| `require_hr` | `hr` | HR actions |
| `require_org_staff` | `hr`, `super_admin` | org administration screens |
| `require_workforce` | `hr`, `employee`, `super_admin` | attendance/leave/payslip portals |
| `require_super_admin` | `super_admin` | organizations + design studio |

- Registration rules (`auth.service.register`): only `hr` or `candidate` can be requested; the first `hr` wins, later HR requests degrade to `candidate`; `super_admin` and `employee` are seeded/managed.
- The API returns HTTP `401` (bad/absent token), `403` (role not allowed), and structured `409 {code, message}` for business conflicts.

## 4. Multi-tenancy

Every tenant-scoped table carries an `organization_id` foreign key. Row scoping is applied at the query layer in each router — not in the frontend:

- List/filter queries always start from the current user's `organization_id` (or a `__none__` sentinel for HR queries in `candidates/router.py`).
- Object access helpers check `record.organization_id == user.organization_id` before returning or mutating.
- `super_admin` bypasses org filters so it can administer all tenants.
- `workforce.assert_org` centralizes the "must belong to org X" check.
- Smart Chat document search filters by `organization_id` and by visibility (`employee_visible` / `candidate_visible`), so tenants never see each other's policies or knowledge.

Public surfaces that must be open are intentionally narrow: the open-jobs list and the apply endpoint are the only read paths without a token, and each is scoped to jobs with status `open`.

## 5. Data model (app/models.py)

Core identity & tenancy:

- `User` — email (encrypted) + unique `email_hash`, password hash, role, org, soft delete.
- `Organization` — name/slug, status, theme/layout keys, enabled modules, theme overrides.
- `Department` — per-org departments (currently metadata; people carry a free-text `department`).

Workforce:

- `Employee` — per-org; links to `User` (optional), department/designation, manager, status, joining date.
- `AttendanceRecord` — per employee per `work_date` (unique), check-in/out timestamps, status.
- `LeaveType` — per-org leave definitions; `LeaveBalance` — per employee per type per year (unique); `LeaveRequest` — start/end/days/status/decider.
- `SalaryStructure` — basic/HRA/allowance/tax%/deductions per employee.
- `PayrollRun` — per-org monthly run (unique period); `Payslip` — per run per employee with computed gross/tax/net.

Recruitment:

- `Job` — title/team/skills/years/education, narrative + generated JD, status, `created_by` HR, optional org.
- `Application` — per job per candidate (unique), status, resume path, encrypted parsed text, keyword/LLM scores, HR override.
- `Interview` — application-scoped schedule + Google event link + status.
- `CalendarBlock`, `HrWorkingHours` — HR availability.
- `Message` — in-app inbox item (optional SMTP flag); `Feedback` — post-interview rating/notes.

AI & knowledge:

- `KnowledgeDocument` — per-org HR policies/handbook with category, version, visibility flags.
- `KnowledgeChunk` — chunked sections per document for lexical/RAG search.
- `ChatConversation`, `ChatMessage` — per-user chat history; assistant messages store the `agents` and `sources` that produced them.

Governance: `AuditLog`, `RetentionSettings`.

## 6. Smart Chat copilot flow

See `docs/SMART_CHAT.md` for the full description. In one line:

```
Chat UI → JWT → User Context Resolver → Supervisor/router → agents
  (RAG over org KnowledgeDocuments, live employee/candidate tools)
  → grounded answer + sources + optional LLM synthesis
```

## 7. Design studio & theming

- Catalog in `app/themes.py`: 8 `THEMES` (each a full token set), 6 `LAYOUTS`, and an `ALL_MODULES` list beyond the `DEFAULT_MODULES` enabled per org.
- Super admin assigns a theme/layout/module set per org; `serialize_org` resolves a theme including per-org overrides.
- Frontend `stores/auth.js` calls `theme.js.applyTheme(...)` after login/load to map tokens onto CSS variables (`--terra`, `--paper`, …).

## 8. Screening pipeline (recruitment)

`apply → parsed → screened → shortlisted → interview → technical → hr_round → offer | rejected`

- `modules/pipeline.py` owns `STAGES` and `ALLOWED` transitions and raises `IllegalTransition` for invalid jumps, enforcing offer-after-feedback and interview-row requirements.
- `modules/screening/` parses resumes (text), runs keyword scoring against job skills, and optionally asks an LLM for a 0–100 score + rationale.
- HR can override (pass/fail), paste parsed text, advance, send offers, accept/decline/withdraw flows are available to candidates/HR.

## 9. Security notes

- Passwords hashed with bcrypt (passlib).
- PII encrypted at rest with Fernet; email lookups use HMAC hashes so plaintext is never indexed.
- Rate-limit the ATS/public endpoints appropriately when exposed; the current focus is correctness of tenant isolation.
- LLM calls go through optional `USER_LLM_*` env keys only; the platform's own keys are never read or embedded.

## 10. Testing

- Backend: `pytest` under `backend/tests/`; each module has a focused test file using an in-memory SQLite DB and an app with dependency-overridden session. Roles, tenant isolation, transitions, payroll math, GDPR, and chat grounding are covered.
- Frontend: `vitest` + `@vue/test-utils` under `frontend/src/__tests__/`.
