# API Reference

Base URL for all endpoints: `/api`. Authentication is a JWT in the `Authorization: Bearer <token>` header except where noted "public". Interactive docs are available at `/docs` when the backend is running.

Legend — required role:

- **auth** = any authenticated user
- **hr** = role `hr`
- **staff** = `hr` or `super_admin`
- **workforce** = `hr`, `super_admin`, or `employee`
- **admin** = `super_admin`
- **public** = no token needed
- Scoped objects are always checked against the caller's `organization_id`.

## Auth (`/api/auth`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | public | Register; first `hr` wins, otherwise `candidate` |
| POST | `/auth/login` | public | Login, returns `{token, user}` |
| GET | `/auth/me` | auth | Current user profile + serialized org |

## Organizations / design studio (`/api/orgs`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/orgs/themes` | auth | List available themes |
| GET | `/orgs/layouts` | auth | List available layouts |
| GET | `/orgs/modules` | auth | List toggleable modules |
| GET | `/orgs` | admin | List organizations |
| POST | `/orgs` | admin | Create organization (theme/layout/modules) |
| PATCH | `/orgs/{org_id}` | admin | Update branding, theme, layout, modules, overrides |

## Employees (`/api/employees`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/employees` | staff | List org employees |
| POST | `/employees` | staff | Create employee record |
| GET | `/employees/{id}` | staff | Employee detail (org-scoped) |
| PATCH | `/employees/{id}` | staff | Update employee |

## Attendance (`/api/attendance`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/attendance/today` | staff | Daily board with present/late/absent/on-leave counts |
| GET | `/attendance/me` | workforce | Caller's recent attendance |
| POST | `/attendance/check-in` | workforce | Check in today (late after 09:30 UTC) |
| POST | `/attendance/check-out` | workforce | Check out today |
| POST | `/attendance/correct` | staff | Correct/mark attendance status |

## Leave (`/api/leave`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/leave/types` | workforce | List org leave types |
| POST | `/leave/types` | staff | Create leave type |
| GET | `/leave/balances` | workforce | Balances (own for employee, org for staff) |
| GET | `/leave/requests` | workforce | Requests (own for employee, org for staff) |
| POST | `/leave/requests` | workforce | Apply (weekday calc, overlap + balance checks) |
| POST | `/leave/requests/{id}/decide` | staff | Approve / reject pending request |

## Payroll (`/api/payroll`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/payroll/structures` | staff | Salary structures |
| POST | `/payroll/structures` | staff | Create/update structure (org-scoped employee) |
| GET | `/payroll/runs` | staff | Monthly runs with totals |
| POST | `/payroll/runs` | staff | Create run (draft) from active structures |
| POST | `/payroll/runs/{id}/process` | staff | Mark processed |
| GET | `/payroll/runs/{id}` | staff | Run detail with payslips |
| GET | `/payroll/summary` | staff | Aggregated processed/draft + totals |
| GET | `/payroll/payslips` | workforce | Own payslips (employee) or org payslips (staff) |
| GET | `/payroll/payslips/{id}` | workforce | Payslip detail (org/self scoped) |

## Jobs / recruitment (`/api/jobs`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/jobs` | public* | Open jobs (public list) / all jobs for HR |
| GET | `/jobs/{id}` | public* | Job detail incl. generated JD |
| POST | `/jobs` | hr | Create job |
| PATCH | `/jobs/{id}` | hr | Update job |
| POST | `/jobs/{id}/publish` | hr | Set status open |
| POST | `/jobs/{id}/close` | hr | Close job |
| GET | `/jobs/{id}/export.md` | auth | Markdown JD export |
| GET | `/jobs/{id}/export.pdf` | auth | PDF JD export |
| POST | `/jobs/{id}/apply` | public | Apply (multipart resume + email/password/name) |

\* `*` public read only shows `open` jobs; an authenticated HR sees org jobs regardless of status.

## Applications (`/api/applications`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/applications` | auth | Org apps (HR) or own apps (candidate) |
| GET | `/applications/{id}` | auth | Detail + interviews (owner or HR) |
| GET | `/applications/{id}/resume` | auth | Resume file (owner or HR) |
| POST | `/applications/{id}/override` | hr | HR screening override pass/fail |
| POST | `/applications/{id}/parsed-text` | hr | Paste parsed resume text |
| POST | `/applications/{id}/advance` | hr | Advance pipeline stage |
| POST | `/applications/{id}/offer` | hr | Send offer (requires feedback) |
| POST | `/applications/{id}/reject` | hr | Reject (post-interview requires feedback) |
| POST | `/applications/{id}/accept-offer` | candidate | Accept offer |
| POST | `/applications/{id}/decline-offer` | candidate | Decline offer |
| POST | `/applications/{id}/withdraw` | candidate | Withdraw application |

## Calendar & interviews (`/api`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/calendar/slots` | candidate/hr | Available slots for an HR within a range |
| GET | `/calendar/hours` | hr | Own working hours |
| PUT | `/calendar/hours` | hr | Set working hours |
| GET | `/calendar/blocks` | hr | Own availability blocks |
| POST | `/calendar/blocks` | hr | Create block |
| DELETE | `/calendar/blocks/{id}` | hr | Remove block |
| POST | `/interviews` | hr | Schedule interview |
| POST | `/interviews/{id}/confirm` | candidate | Confirm interview |
| POST | `/interviews/{id}/cancel` | auth | Cancel interview |
| POST | `/interviews/{id}/complete` | hr | Complete interview |
| GET | `/calendar/google/connect` | hr | Start Google OAuth |
| GET | `/calendar/google/callback` | hr | OAuth callback |
| POST | `/calendar/google/disconnect` | hr | Disconnect Google |

## Inbox / mail (`/api/messages`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/messages` | auth | Own inbox messages |
| POST | `/messages/{id}/read` | auth | Mark read |
| POST | `/messages/{id}/retry-smtp` | hr | Retry SMTP delivery |

## Interview feedback (`/api/feedback`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/feedback` | hr | Submit rating + notes for an interview |

## GDPR / self-service (`/api`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/hr/dashboard` | hr | Dashboard stats (jobs/pipeline/interviews/employees) |
| GET | `/me/export` | auth | Export own PII data (candidates) |
| DELETE | `/me` | auth | Delete own account/data (GDPR) |
| GET | `/candidates/{id}/export` | hr | Export a candidate's data |

## Smart Chat (`/api/chat`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/chat/context` | auth | Resolved identity context from JWT (employee/candidate) |
| GET | `/chat/conversations` | auth | List caller's conversations |
| GET | `/chat/conversations/{id}` | auth | Messages + agents + sources for a conversation |
| POST | `/chat/messages` | auth | Ask the copilot (message + optional conversation_id) |
| GET | `/chat/documents` | hr | List org knowledge documents |
| POST | `/chat/documents` | hr | Create + index a policy/document |

Response of `POST /chat/messages` includes `reply`, `conversation_id`, `agents`, `sources`, `cards`, `activity`, `context`, and `denied_cross_user`.

## Error conventions

- `401` — missing/invalid JWT.
- `403` — authenticated but wrong role / out-of-org object.
- `404` — not found (scoped queries hide cross-tenant rows).
- `409` — business conflict, body `{"code": "...", "message": "..."}` (e.g. `duplicate_period`, `overlap`, `already_checked_in`, `offer_requires_feedback`).
- `422` — validation / invalid date or period.
