# Mapping to the SmartHRMS AI Design Reference

This is an honest build/gap matrix between the attached **SmartHRMS AI** enterprise spec (`.monkeycode-tmp-files/41f2fac4-long-input-20260907-072634.txt`) and what **Northstar HRMS** implements today.

The repo deliberately keeps its own pragmatic stack (**FastAPI + Vue 3 + SQLite**) rather than the spec's MongoDB/React/TypeScript target. Functionality is implemented natively where it matters; Mongo-specific notes are flagged below. Status: **built** = works end to end today · **partial** = exists with caveats · **gap** = not implemented.

## Platform & foundation

| Spec section | Status | Notes |
| --- | --- | --- |
| 1 Product name | built | Northstar HRMS (SmartHRMS-class), multi-tenant |
| 2 Tech stack | partial | FastAPI + SQLAlchemy + Vue 3 instead of MongoDB/React; same patterns (Pydantic, JWT, Vite) |
| 3 Multi-tenant org architecture | built | `Organization` + `organization_id` on all tenant tables; server-side row scoping; super-admin bypass |
| 4 Authentication | partial | Email+password + JWT. No employee/candidate-ID login, no forgot/reset-password flow |
| 5 RBAC | built | 4 roles (`super_admin`, `hr`, `employee`, `candidate`); no custom roles/permissions tables |
| 6 Dynamic sidebar | built | Role-aware nav, org module toggles |
| 7–10 UI reference, glassmorphism, themes, responsive | partial | Tokenized theme system + design studio; not the spec's exact glass/React design |
| 11 Main dashboard | built | HR dashboard (jobs/pipeline/interviews/employees) |
| 12 Employee module | built | Directory CRUD |
| 13 Attendance | built | Check-in/out, daily board, corrections |
| 14 Leave | built | Types, balances, apply, approve/reject |
| 15 Payroll | built | Structures, monthly runs, payslips |
| 16 Recruitment | built | Full ATS (see MODULES §7) |
| 17 Onboarding | built | Hire → employee + joining checklist + welcome message; HR offboarding with exit date |
| 18 Performance | gap | Module toggle reserved only |
| 19 Learning & development | gap | Module toggle reserved only |
| 20 Document management | partial | Knowledge/policy documents for chat only; no employee document center |
| 21 Compliance | gap | Not built |
| 22 Asset management | gap | Not built |
| 23 Helpdesk | gap | Not built |
| 24 Travel & expense | gap | Not built |
| 25 Workflow engine | gap | Fixed pipeline transitions only; no generic workflow/approval engine |
| 26 Notifications | partial | In-app inbox + unread badge + optional SMTP; no WebSocket/live push |
| 27 Search system | partial | Chat RAG search; no global people search across modules |

## AI / Smart Chat

| Spec section | Status | Notes |
| --- | --- | --- |
| 28 AI Smart Chat / HR Copilot | built | Floating copilot, JWT identity, grounded answers |
| 29 Multi-agent AI | built | Router + employee_data / candidate_data / leave / attendance / payroll / rag / hr_policy / recruitment agents |
| 30 Supervisor agent | built | `chat/supervisor.py` orchestrates agents → synthesizer |
| 31 RAG architecture | built | Chunked org-scoped knowledge docs, visibility filtering |
| 32 Hybrid search | built | Lexical + TF-cosine + keyword fusion + rerank; no embedding/vector search |
| 33 RAG security | built | Tenant + visibility filtering; per-user data tools |
| 34 AI tool calling | built | Typed authorized accessors (tools.py); LLM never runs SQL |
| 35 AI action confirmation | gap | Copilot is read-only; no action-taking tools yet |
| 36 Chat UI | built | Floating widget: sources, cards, activity, new chat, history |
| 37 AI observability | partial | Agent/source metadata persisted per message; no tracing dashboard |
| 38 Admin AI configuration | partial | Docs via API; no AI-config admin screen |
| 39 Organization-specific AI | built | Policies/knowledge per org, org-scoped search |

## Platform operations

| Spec section | Status | Notes |
| --- | --- | --- |
| 40 Super admin panel | built | Orgs CRUD + design studio |
| 41 Dynamic module configuration | built | Org module toggles drive nav/UI |
| 42 People search | gap | Not built |
| 43 Icon system | partial | Inline SVG chat icons; app uses text/CSS styling |
| 44 UI component architecture | partial | Vue SFCs + shared CSS tokens; not shadcn-style |
| 45 Frontend routing | built | Role-guarded Vue Router |
| 46 Backend architecture | built | Modular FastAPI monolith, per-module routers |
| 47 AI backend architecture | partial | Context→router→agents→synthesizer exists; no async job infra |
| 48 API design | built | See docs/API_REFERENCE.md |
| 49 Audit logging | built | `AuditLog` + `log_action` on key writes |
| 50 Security | partial | JWT, bcrypt, Fernet PII, tenant isolation; no rate limiting/WebSocket |
| 51 AI guardrails | built | Identity from session, cross-user denial, grounded refusals, no identity-ask prompts |
| 52 Database design | partial | SQLite relational model; not MongoDB collections |
| 53–54 Seed data & demo users | built | Idempotent `scripts/seed.py` + demo logins |
| 55–57 Testing | built | pytest module suites + Vitest component tests; no E2E |
| 58 Error handling | built | Structured 401/403/404/409/422 conventions |
| 59 Documentation | built | This tree: README + ARCHITECTURE + API_REFERENCE + MODULES + SMART_CHAT |

## Highest-value gaps (extension backlog)

1. **Document center** (employee documents + compliance) — reuse org-scoped `KnowledgeDocument` pattern.
2. **Workflow engine + approvals** — generalize the pipeline-transition approach for leave/expense/asset approvals.
3. **Notifications via WebSocket** — event bus alongside in-app inbox.
4. **Manager role / portal** — people queries and team views for `manager_id`.
5. **Performance, training, assets, helpdesk, travel & expense** — module toggles already reserve names.
6. **Global search + people search**, **forgot/reset password**, **custom roles/permissions tables**.
7. **Optional vector embeddings** behind the existing RAG interface when external embedding services are allowed.
