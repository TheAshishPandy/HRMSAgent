# Module Guide

Functional description of each module, the roles that use it, and where it lives. The frontend nav is role-aware and, for HR/employee portals, further filtered by the organization's enabled `modules` list (see `frontend/src/components/AppShell.vue`).

---

## 1. Multi-tenant organizations & branding

**Roles:** `super_admin` · **Screens:** `/admin`, `/admin/studio`

Super admins create organizations and configure each one's identity:

- **Theme** — one of 8 tokenized themes (`corporate_blue`, `modern_purple`, `emerald`, `dark_enterprise`, `minimal`, …) with optional per-org color overrides.
- **Layout** — sidebar/top/compact/mobile-first shell variants.
- **Modules** — toggle feature modules (dashboard, employees, recruitment, attendance, leave, payroll, performance, training, documents, expense, assets, helpdesk, reports, analytics, chatbot).
- Nav hides disabled modules automatically.

**Tenant isolation** is enforced server-side: every employees/attendance/leave/payroll/recruitment/chat query is filtered by the caller's `organization_id`. See `docs/ARCHITECTURE.md §4`.

## 2. Authentication & roles

**Roles:** all · **Screens:** `/login`, `/register`

Email+password with bcrypt hashing; PII encrypted at rest (Fernet). Roles gate both API access and frontend routes:

- `super_admin` → organization administration + design studio.
- `hr` → People, Onboarding, Attendance, Leave, Payroll, Jobs/Pipeline, Calendar, Inbox, Smart Chat, Settings.
- `employee` → My work (check-in/out), Onboarding checklist, Leave, Payslips, Inbox, Smart Chat.
- `candidate` → My applications, Inbox, Smart Chat, Open roles.

## 3. Employees (People directory)

**Roles:** staff (manage) · **Screens:** `/hr/employees`

Directory CRUD per org: name, email, department, designation, manager, status (active/inactive), joining date, exit date/reason. Employees link to a `User` so they can sign in to the `/work` portal. HR can offboard an active employee from this screen.

## 4. Attendance

**Roles:** workforce · **Screens:** `/work`, `/hr/attendance`

- **Employee:** check in / check out once per day; check-in after 09:30 UTC is flagged `late`. Past records are visible on the My Work home.
- **HR:** daily board with counts (present, late, absent, on leave, remote, half day) and status corrections.

Rules: one record per employee per date (unique constraint); no duplicate check-in/out; approved leave marks the day `on_leave`.

## 5. Leave management

**Roles:** workforce · **Screens:** `/work/leave`, `/hr/leave`

- Leave types per org (annual/sick/casual…) with per-year entitlement.
- Yearly balances per employee per type.
- Apply for a range; only **weekday** days are counted; overlapping requests and insufficient balance are rejected with structured 409s.
- HR approves or rejects pending requests; approval deducts from the balance.

## 6. Payroll

**Roles:** staff + employee · **Screens:** `/hr/payroll`, `/work/payslips`

- Salary structures per employee: basic, HRA, allowance, tax %, other deductions.
- Monthly run creates draft payslips for every active employee with a structure; run totals (gross/tax/deductions/net) are computed server-side. Duplicate periods conflict (409).
- Processed runs make payslips visible to employees in `/work/payslips`.
- Employees only ever see their own payslips; HR sees all payslips for the org.

## 7. Recruitment / ATS

**Roles:** hr, candidate · **Screens:** `/`, `/jobs/:id`, `/hr/jobs/*`, `/hr/jobs/:id/pipeline`, `/hr/applications/:id`, `/me`, `/me/applications/:id`

The most developed module. Public open roles list + detail; applying uploads a resume (txt/pdf/docx), then:

1. **Parse** the resume to text.
2. **Screening** — keyword scoring against required/nice-to-have skills, optional LLM 0–100 ranking via `USER_LLM_*`.
3. **Pipeline** — the application moves through stages: `applied → screened → shortlisted → interview → technical → hr_round → offer`, with rejection/withdrawal at several points. Transitions are validated (`modules/pipeline.py`): offers require an interview + feedback; post-interview rejections require feedback.
4. **HR actions** — override screening, paste parsed text, advance stage, schedule interviews from availability slots, submit interview feedback, send offer.
5. **Candidate actions** — view status + interview times, pick a slot, confirm/cancel, accept/decline offer, withdraw.
6. **Calendar** — HR working hours and blocks; candidate-facing slot picker; optional Google Calendar OAuth sync; weekday-only scheduling (409 `weekend_not_allowed` on weekends).
7. **Inbox** — every state change writes an in-app message; SMTP optional.
8. **GDPR** — candidates can export their data (`/api/me/export`) and delete their account (`DELETE /api/me`); HR can export a candidate's data.

Job JD generation and Markdown/PDF export are available in the HR job editor.

## 8. Onboarding / offboarding

**Roles:** hr (start + track), employee (complete checklist) · **Screens:** `/hr/onboarding`, `/work/onboarding`, `/hr/employees`

- **Eligible hires** — applications in `hired` (offer accepted) that do not yet have an onboarding record.
- **Start onboarding** — HR sets department, designation, joining date. Creates the employee profile, converts the candidate account to `employee`, seeds leave balances, writes a joining checklist, and sends a welcome inbox message.
- **Checklist** — default tasks: offer letter, government ID, bank details, IT/laptop, HR induction. Employee or HR marks tasks done; the record auto-completes when every task is done.
- **Offboarding** — HR sets exit date + reason on an active employee; status becomes `inactive` and an inbox notice is sent.

Demo seed includes `eli@example.com` already hired for Backend Engineer so HR can start onboarding immediately.

## 9. Design studio

**Roles:** `super_admin` · **Screens:** `/admin/studio`

Pick an org, then set its theme, layout, module set, and raw token overrides. The org's branding is applied to every user in that org after login via CSS custom properties.

## 10. Smart Chat (AI copilot)

**Roles:** workforce + candidate (floating widget on all signed-in pages) · **Screens:** embedded in `App.vue`

A floating chat that already knows the user from the JWT — it never asks for employee/candidate ID, name, department, or company. It answers:

- **Policy/RAG questions** — grounded in org-scoped, visibility-filtered `KnowledgeDocuments` (hybrid lexical search; source cards cited).
- **Live employee data** — leave balances/requests, attendance, payslips, profile (department, designation, joining date, manager).
- **Live candidate data** — application status, job applied, interview schedule, recruiter.
- **Combined questions** — e.g. "Can I take 10 days leave?" merges balance + policy eligibility.
- **Conversational follow-ups** — conversation memory lets "How many are casual?" refer to the previous question.

HR can manage org policy documents under the chat's `/api/chat/documents` endpoints; seeded policies (Leave, Payroll, Attendance, Handbook, Candidate Guidelines, Code of Conduct) come with the seed data.

See `docs/SMART_CHAT.md` for architecture and behavior guarantees.

## 11. Not implemented yet

The following SmartHRMS spec areas are **not built** in this repo today and are the primary extension backlog:

- Performance management (appraisals, goals, 360)
- Learning & development / training
- Document management center (beyond chat policy docs) & compliance
- Asset management
- Helpdesk tickets
- Travel & expense
- Generic workflow engine + approval routing
- Global people search
- WebSocket live notifications
- MongoDB persistence (the spec's stack is MongoDB/React; this repo is SQLite/FastAPI/Vue)

See `docs/SPEC_MAPPING.md` for the full build/gap matrix.
