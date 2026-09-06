# Northstar HRMS

Multi-tenant HR platform. Recruitment (ATS) is the first live module: jobs, resume screening, weekday interviews, in-app inbox, optional SMTP / Google Calendar / LLM ranking. Day 1 also includes organizations, super-admin, employees, and CSS theme tokens.

## Setup

Generate an encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy `.env.example` to `backend/.env` and set `JWT_SECRET` (32+ chars) and `DATA_ENCRYPTION_KEY`.

Install and run the API:

```bash
pip install --break-system-packages -r backend/requirements.txt
cd backend
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Seed demo data (from `backend/`):

```bash
PYTHONPATH=. python scripts/seed.py
```

Demo logins (password for all: `password`):

- Super admin: `admin@example.com`
- HR: `hr@example.com`
- Employee: `sam.lee@example.com`
- Candidates: `ada@example.com` and other seeded applicants

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Tests

```bash
cd backend && PYTHONPATH=. pytest -q
cd frontend && npm test
```

Optional env vars (`USER_LLM_*`, `SMTP_*`, `GOOGLE_*`) enable extra features. The core flow works without them.
