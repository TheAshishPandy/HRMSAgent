# Northstar HRMS

A multi-tenant HR platform ("SmartHRMS-class") with an HR-driven recruitment/ATS core plus workforce modules, a per-organization design studio, and a JWT-aware, RAG-based AI copilot.

The system is fully functional end to end: FastAPI + SQLAlchemy backend, Vue 3 single-page frontend, SQLite storage, and a live multi-agent Smart Chat that answers questions from the authenticated session plus organization-scoped policy documents.

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (typed ORM), Pydantic v2, JWT auth, Fernet PII encryption, SQLite
- **Frontend:** Vue 3, Vue Router, Vite, Vitest
- **AI:** optional OpenAI-compatible chat completion for resume ranking and chat synthesis; grounded RAG is fully functional without it

## Feature summary

| Area | What is implemented |
| --- | --- |
| Multi-tenancy | Organizations, org-scoped isolation at the query layer, org branding/theme/layout |
| Auth & RBAC | Email+password, JWT; roles `super_admin`, `hr`, `employee`, `candidate` |
| Employees | People directory CRUD, department/designation, manager link, active/inactive, joining + exit |
| Attendance | Daily check-in / check-out, present/late/absent board, HR corrections |
| Leave | Leave types, per-year balances, apply, weekday calculation, HR approve/reject |
| Payroll | Salary structures, monthly runs, payslips (gross/tax/net), process runs |
| Recruitment (ATS) | Jobs + JD generation/export, public apply with resume, keyword + optional LLM screening, 8-stage pipeline (applied → hired/rejected), interviews, feedback, offers, in-app inbox, GDPR export/delete |
| Onboarding | Hired candidate → employee + joining checklist + welcome message; HR offboarding with exit date/reason |
| Calendar | Working hours, availability blocks, interview slot picker, weekday guard |
| Design studio | 8 themes, 6 layouts, toggleable modules, theme overrides per org |
| Smart Chat | Floating AI copilot with context resolver, agent router, hybrid RAG over HR policies, live leave/payroll/attendance/application tools, source citations |

## Roles

| Role | Access |
| --- | --- |
| `super_admin` | All orgs; manage organizations + design studio |
| `hr` | Org-scoped staff: employees, onboarding, attendance, leave, payroll, recruitment, documents, chat |
| `employee` | `/work` portal: own attendance, onboarding checklist, leave, payslips, inbox, chat |
| `candidate` | `/me` portal: own applications, interviews, offers, chat |

Registration can create the first `hr`; later registrations default to `candidate`. `super_admin` and `employee` are created via seed or by an org admin.

## Repository layout

```
backend/
  app/
    main.py          FastAPI app + router wiring
    config.py        env settings
    crypto.py        Fernet PII encryption + email hashing
    db.py            engine / session / SQLite migrations
    models.py        SQLAlchemy models (all modules)
    deps.py          auth deps: get_current_user, require_hr, require_org_staff, require_workforce
    themes.py        theme/layout/module catalog
    modules/
      auth/          register, login, /me
      tenants/       organizations, themes, layouts, modules
      employees/     people directory
      onboarding/    hire checklist + offboarding
      attendance/    check-in/out, daily board, corrections
      leave/         types, balances, requests, decisions
      payroll/       structures, runs, payslips
      jobs/          job CRUD, publish/close, JD generation, exports
      candidates/    apply, applications, pipeline actions, GDPR
      calendar/      hours, blocks, slots, interviews
      mail/          in-app inbox + optional SMTP
      feedback/      interview feedback
      screening/     resume parse, keyword + optional LLM scoring
      chat/          Smart Chat copilot (context, router, RAG, tools)
frontend/
  src/
    components/      AppShell, PipelineBoard, SlotPicker, StatusBanner, SmartChat
    views/           per-role pages (admin/hr/work/me/public)
    api.js           fetch wrapper (JWT header)
    stores/auth.js   session + theme application
    router.js        role-guarded routes
    theme.js         applies org theme tokens to CSS
docs/                architecture, API, module, AI, spec-mapping guides
```

See `docs/ARCHITECTURE.md` for a deeper look and `docs/SPEC_MAPPING.md` for how this compares with the enterprise SmartHRMS AI design reference.

## Quickstart

### 1. Backend

Generate an encryption key (any Fernet key works):

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Create `backend/.env` (copy `.env.example` from the repo root into `backend/`) and set `JWT_SECRET` (32+ chars) and `DATA_ENCRYPTION_KEY`. The API refuses to start without both.

```bash
pip install --break-system-packages -r backend/requirements.txt
cd backend
PYTHONPATH=. python3 scripts/seed.py        # demo data (idempotent)
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173, proxies /api to :8000
```

The Vite dev server already allows `*.monkeycode-ai.live` hosts for preview.

### Demo logins (password for all: `password`)

| Login | Role |
| --- | --- |
| `admin@example.com` | super admin |
| `hr@example.com` | HR |
| `sam.lee@example.com` | employee |
| `ada@example.com` ... | candidates seeded with applications |

Seed data also creates leave types and balances, an August 2026 payroll run + payslips, two open jobs with pipeline applications, HR policy documents for Smart Chat, and a demo hire (`eli@example.com`, hired Backend Engineer) ready for onboarding.

## Testing

```bash
cd backend && PYTHONPATH=. python3 -m pytest -q
cd frontend && npm test
```

## Optional features (env)

- `USER_LLM_API_KEY` / `USER_LLM_BASE_URL` / `USER_LLM_MODEL` — resume LLM ranking and Smart Chat answer synthesis. Without them, keyword screening and grounded RAG answers still work.
- `SMTP_*` — send emails in addition to in-app inbox messages.
- `GOOGLE_*` — Google Calendar sync for interviews (falls back to local weekday logic).
