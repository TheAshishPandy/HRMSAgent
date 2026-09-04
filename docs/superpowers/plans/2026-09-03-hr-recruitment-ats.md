# HR Recruitment ATS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a local ATS web app where HR can take a candidate from job post to offer or rejection, with candidate accounts, weekday-only interviews, in-app inbox, and optional Google/SMTP/LLM.

**Architecture:** Vue 3 SPA talks to a FastAPI modular monolith over `/api`. SQLite stores encrypted PII. Missing Google, SMTP, or LLM credentials degrade features; core flow still works.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, passlib bcrypt, PyJWT, cryptography Fernet, pypdf, python-docx, httpx, pytest; Vue 3, Vue Router, Vite, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-03-hr-recruitment-ats-design.md`

## Global Constraints

- No live LinkedIn/Indeed posting or scraping; internal careers board only.
- Project LLM vars are `USER_LLM_API_KEY`, `USER_LLM_BASE_URL`, `USER_LLM_MODEL` only. Never read `MCAI_LLM_*`.
- Missing Google, SMTP, or LLM must not block jobs, apply, keyword screening, local scheduling, or in-app mail.
- Server rejects Saturday/Sunday interview starts (`409`, `weekend_not_allowed`).
- PII encrypted at rest with Fernet (`DATA_ENCRYPTION_KEY`). Process must refuse to start if that key or `JWT_SECRET` is missing.
- First register may create `hr`; later registers are `candidate` unless seeded.
- Vite `server.allowedHosts` includes `.monkeycode-ai.live`. Proxy `/api` to `http://127.0.0.1:8000`.
- Do not add comments unless the existing file already uses them for that pattern.
- No emoji in UI copy or code.

---

## File map

```
backend/
  requirements.txt
  alembic.ini
  alembic/env.py
  alembic/script.py.mako
  alembic/versions/001_initial.py
  app/__init__.py
  app/main.py
  app/config.py
  app/db.py
  app/models.py
  app/crypto.py
  app/deps.py
  app/errors.py
  app/modules/auth/__init__.py
  app/modules/auth/router.py
  app/modules/auth/service.py
  app/modules/auth/schemas.py
  app/modules/jobs/__init__.py
  app/modules/jobs/router.py
  app/modules/jobs/service.py
  app/modules/jobs/schemas.py
  app/modules/jobs/jd.py
  app/modules/candidates/__init__.py
  app/modules/candidates/router.py
  app/modules/candidates/service.py
  app/modules/candidates/schemas.py
  app/modules/screening/__init__.py
  app/modules/screening/service.py
  app/modules/screening/parse.py
  app/modules/screening/score.py
  app/modules/screening/llm.py
  app/modules/calendar/__init__.py
  app/modules/calendar/router.py
  app/modules/calendar/service.py
  app/modules/calendar/google.py
  app/modules/mail/__init__.py
  app/modules/mail/service.py
  app/modules/mail/templates.py
  app/modules/mail/router.py
  app/modules/feedback/__init__.py
  app/modules/feedback/router.py
  app/modules/feedback/service.py
  app/modules/pipeline.py
  app/modules/audit.py
  tests/conftest.py
  tests/test_auth.py
  tests/test_jobs.py
  tests/test_screening.py
  tests/test_apply.py
  tests/test_calendar.py
  tests/test_mail.py
  tests/test_pipeline.py
  tests/test_gdpr.py
  scripts/seed.py
frontend/
  package.json
  vite.config.ts
  index.html
  src/main.js
  src/App.vue
  src/api.js
  src/router.js
  src/style.css
  src/stores/auth.js
  src/views/LoginView.vue
  src/views/RegisterView.vue
  src/views/HrDashboard.vue
  src/views/JobsListView.vue
  src/views/JobEditView.vue
  src/views/PipelineView.vue
  src/views/ApplicationDetailView.vue
  src/views/CalendarView.vue
  src/views/InboxView.vue
  src/views/SettingsView.vue
  src/views/PublicJobsView.vue
  src/views/PublicJobDetailView.vue
  src/views/CandidateDashboard.vue
  src/views/CandidateApplicationView.vue
  src/components/AppShell.vue
  src/components/PipelineBoard.vue
  src/components/SlotPicker.vue
  src/components/StatusBanner.vue
  src/__tests__/PipelineBoard.spec.js
  src/__tests__/SlotPicker.spec.js
  src/__tests__/ApplyForm.spec.js
.env.example
README.md
```

---

### Task 1: Backend scaffold, config, crypto boot check

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/crypto.py`
- Create: `backend/app/errors.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py` (boot-check tests live here first, then auth in Task 3)
- Create: `.env.example`
- Modify: `.gitignore` (add `data/`, `backend/.env`, `frontend/dist/`)

**Interfaces:**
- Consumes: nothing
- Produces: `Settings` from `app.config.get_settings()`; `encrypt_str(plain: str) -> str`, `decrypt_str(token: str) -> str`, `hmac_email(email: str) -> str`; FastAPI app that 500s/exits if keys missing

- [ ] **Step 1: Write the failing boot test**

Create `backend/tests/test_config.py`:

```python
import os
import pytest
from cryptography.fernet import Fernet


def test_get_settings_requires_jwt_and_encryption_key(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        get_settings()


def test_encrypt_roundtrip(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", key)
    monkeypatch.setenv("JWT_SECRET", "test-secret-at-least-32-chars-long")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import crypto
    crypto.reset()
    token = crypto.encrypt_str("ada@example.com")
    assert token != "ada@example.com"
    assert crypto.decrypt_str(token) == "ada@example.com"
    assert crypto.hmac_email("Ada@example.com") == crypto.hmac_email("ada@example.com")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pip install --break-system-packages -q pytest cryptography pydantic-settings && PYTHONPATH=. pytest tests/test_config.py -v`

Expected: FAIL (app.config missing)

- [ ] **Step 3: Write minimal implementation**

`backend/requirements.txt`:

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
alembic==1.14.0
pydantic==2.10.4
pydantic-settings==2.7.0
passlib[bcrypt]==1.7.4
bcrypt==4.2.1
PyJWT==2.10.1
cryptography==44.0.0
pypdf==5.1.0
python-docx==1.1.2
httpx==0.28.1
python-multipart==0.0.20
reportlab==4.2.5
pytest==8.3.4
```

`backend/app/config.py`:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    jwt_secret: str = ""
    data_encryption_key: str = ""
    database_url: str = "sqlite:///./data/ats.db"
    resume_dir: str = "./data/resumes"
    user_llm_api_key: str = ""
    user_llm_base_url: str = ""
    user_llm_model: str = "deepseek-chat"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@localhost"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8000/api/calendar/google/callback"
    public_base_url: str = "http://127.0.0.1:5173"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.jwt_secret or len(s.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET is required and must be at least 32 characters")
    if not s.data_encryption_key:
        raise RuntimeError("DATA_ENCRYPTION_KEY is required")
    return s
```

`backend/app/crypto.py`:

```python
import hashlib
import hmac
from cryptography.fernet import Fernet
from app.config import get_settings

_fernet = None


def reset() -> None:
    global _fernet
    _fernet = None


def _f() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_settings().data_encryption_key.encode())
    return _fernet


def encrypt_str(plain: str) -> str:
    return _f().encrypt(plain.encode()).decode()


def decrypt_str(token: str) -> str:
    return _f().decrypt(token.encode()).decode()


def hmac_email(email: str) -> str:
    key = get_settings().data_encryption_key.encode()
    return hmac.new(key, email.strip().lower().encode(), hashlib.sha256).hexdigest()
```

`backend/app/errors.py`:

```python
from fastapi import HTTPException


def conflict(code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": detail})
```

`backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings


def create_app() -> FastAPI:
    get_settings()
    app = FastAPI(title="ATS")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()
```

`.env.example`:

```
JWT_SECRET=change-me-to-a-32-char-or-longer-secret
DATA_ENCRYPTION_KEY=
DATABASE_URL=sqlite:///./data/ats.db
RESUME_DIR=./data/resumes
PUBLIC_BASE_URL=http://127.0.0.1:5173
USER_LLM_API_KEY=
USER_LLM_BASE_URL=
USER_LLM_MODEL=deepseek-chat
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@localhost
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/calendar/google/callback
```

Document in README that `DATA_ENCRYPTION_KEY` is produced with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

Append to `.gitignore`:

```
data/
backend/data/
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd backend && PYTHONPATH=. JWT_SECRET=test-secret-at-least-32-chars-long DATA_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") pytest tests/test_config.py -v`

Expected: PASS (the first test deletes env itself)

- [ ] **Step 5: Commit**

```bash
git add backend .env.example .gitignore
git commit -m "feat: scaffold backend config and PII crypto"
```

---

### Task 2: SQLAlchemy models and test database

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `encrypt_str`, `hmac_email`
- Produces: `get_db()` session; models `User`, `Job`, `Application`, `Interview`, `CalendarBlock`, `HrWorkingHours`, `Message`, `Feedback`, `AuditLog`, `RetentionSettings`

- [ ] **Step 1: Write a failing model smoke test**

`backend/tests/test_models.py`:

```python
from app.models import User, Job
from app.crypto import hmac_email, encrypt_str


def test_user_and_job_persist(db):
    u = User(
        email_enc=encrypt_str("hr@example.com"),
        email_hash=hmac_email("hr@example.com"),
        password_hash="x",
        role="hr",
        name_enc=encrypt_str("Pat HR"),
        timezone="UTC",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    job = Job(
        created_by=u.id,
        title="Backend Engineer",
        team="Platform",
        location="Remote",
        seniority="mid",
        required_skills=["python", "sql"],
        nice_to_have=["aws"],
        min_years=3,
        education="bachelor",
        narrative="Build APIs",
        jd_markdown="# Backend Engineer",
        status="draft",
        screen_threshold=0.6,
    )
    db.add(job)
    db.commit()
    assert job.id is not None
    assert db.query(User).count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. pytest tests/test_models.py -v`

Expected: FAIL (app.models / fixture missing)

- [ ] **Step 3: Write models and conftest**

`backend/app/db.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    url = url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


SessionLocal = None
engine = None


def init_engine():
    global SessionLocal, engine
    engine = make_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`backend/app/models.py` — define all tables from spec section 8:

- `User`: id UUID string PK default `uuid4`, email_enc, email_hash unique, password_hash, role, name_enc, phone_enc nullable, google_refresh_token_enc nullable, timezone default UTC, created_at, deleted_at
- `Job`: fields from spec; `required_skills` and `nice_to_have` as JSON
- `Application`: unique (job_id, candidate_id); status; resume_path; parsed_text_enc; parse_error; keyword_score; score_breakdown JSON; llm_score; llm_rationale; hr_override
- `Interview`, `CalendarBlock`, `HrWorkingHours` unique (hr_user_id, weekday), `Message`, `Feedback` unique interview_id, `AuditLog`, `RetentionSettings` with id=1 retention_days=365

Use `sqlalchemy.orm.Mapped` / `mapped_column`. UUID as `String(36)`.

`backend/tests/conftest.py`:

```python
import os
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-chars-long")
os.environ.setdefault("DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.config import get_settings
get_settings.cache_clear()
from app.db import Base, get_db, make_engine
from sqlalchemy.orm import sessionmaker
from app.main import create_app
from app import models  # noqa: F401


@pytest.fixture
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app = create_app()

    def _get():
        yield db

    app.dependency_overrides[get_db] = _get
    return TestClient(app)
```

Call `Base.metadata.create_all` on startup in `create_app` for v1 (skip Alembic runtime; still add `alembic.ini` stub later if time). Prefer create_all in tests and `main.py` lifespan for SQLite file.

- [ ] **Step 4: Run tests**

Run: `cd backend && PYTHONPATH=. pytest tests/test_models.py tests/test_config.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add ATS SQLAlchemy models"
```

---

### Task 3: Auth register, login, JWT, role guard

**Files:**
- Create: `backend/app/modules/auth/__init__.py`
- Create: `backend/app/modules/auth/schemas.py`
- Create: `backend/app/modules/auth/service.py`
- Create: `backend/app/modules/auth/router.py`
- Create: `backend/app/deps.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/app/main.py` include router

**Interfaces:**
- Consumes: `User`, `hmac_email`, `encrypt_str`, `decrypt_str`
- Produces: `create_token(user_id: str, role: str) -> str`; `get_current_user`; routes `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_auth.py`:

```python
def test_first_register_can_be_hr(client):
    r = client.post("/api/auth/register", json={
        "email": "hr@example.com",
        "password": "password",
        "name": "Pat HR",
        "role": "hr",
    })
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "hr"
    assert "token" in r.json()


def test_second_register_cannot_be_hr(client):
    client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    })
    r = client.post("/api/auth/register", json={
        "email": "other@example.com", "password": "password", "name": "X", "role": "hr"
    })
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "candidate"


def test_login_and_me(client):
    client.post("/api/auth/register", json={
        "email": "c@example.com", "password": "password", "name": "C", "role": "candidate"
    })
    r = client.post("/api/auth/login", json={"email": "c@example.com", "password": "password"})
    token = r.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "c@example.com"


def test_candidate_cannot_create_job(client):
    r = client.post("/api/auth/register", json={
        "email": "c@example.com", "password": "password", "name": "C", "role": "candidate"
    })
    token = r.json()["token"]
    j = client.post("/api/jobs", json={"title": "X"}, headers={"Authorization": f"Bearer {token}"})
    assert j.status_code in (401, 403, 422)
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && PYTHONPATH=. pytest tests/test_auth.py -v`

Expected: FAIL 404

- [ ] **Step 3: Implement auth**

`service.py`: passlib `CryptContext(schemes=["bcrypt"])`; JWT HS256 24h claims `sub`, `role`, `exp`. Register: hash password, encrypt name/email, store email_hash. If `role=="hr"` and a non-deleted hr user exists, force role `candidate`. Login: lookup by email_hash, verify password, skip `deleted_at` users.

`deps.py`: parse Bearer token; 401 if missing/invalid; `require_hr` 403 if role != hr.

`router.py` prefixes `/api/auth`.

Register `auth.router` in `create_app`. Jobs 403 can wait until Task 4; for this task, if `/api/jobs` is missing, change the last test to hit a dummy `GET /api/hr-only` or skip until Task 4. Prefer adding `require_hr` and a placeholder later. **Do not add `/api/jobs` yet.** Remove `test_candidate_cannot_create_job` from this task; add it in Task 4.

- [ ] **Step 4: pytest tests/test_auth.py -v — PASS**
- [ ] **Step 5: Commit** `feat: add JWT auth for HR and candidates`

---

### Task 4: Jobs CRUD, JD template, publish, close, export

**Files:**
- Create: `backend/app/modules/jobs/jd.py`
- Create: `backend/app/modules/jobs/schemas.py`
- Create: `backend/app/modules/jobs/service.py`
- Create: `backend/app/modules/jobs/router.py`
- Create: `backend/tests/test_jobs.py`

**Interfaces:**
- Consumes: `require_hr`, `Job` model
- Produces: `generate_jd(job_fields: dict, apply_url: str) -> str`; routes listed in spec for jobs

- [ ] **Step 1: Failing tests**

```python
def _hr(client):
    r = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    })
    return r.json()["token"]


def test_jd_contains_sections(client):
    token = _hr(client)
    r = client.post("/api/jobs", json={
        "title": "Backend Engineer",
        "team": "Platform",
        "location": "Remote",
        "seniority": "mid",
        "required_skills": ["python", "sql"],
        "nice_to_have": ["aws"],
        "min_years": 3,
        "education": "bachelor",
        "narrative": "Build recruitment APIs.",
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    md = r.json()["jd_markdown"]
    for part in ["Backend Engineer", "Platform", "Remote", "python", "Build recruitment APIs", "How to apply"]:
        assert part in md
    assert r.json()["status"] == "draft"


def test_public_lists_only_open(client):
    token = _hr(client)
    created = client.post("/api/jobs", json={
        "title": "X", "team": "T", "location": "L", "seniority": "j",
        "required_skills": ["go"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "n",
    }, headers={"Authorization": f"Bearer {token}"}).json()
    pub = client.get("/api/jobs")
    assert pub.json() == [] or all(j["status"] == "open" for j in pub.json())
    client.post(f"/api/jobs/{created['id']}/publish", headers={"Authorization": f"Bearer {token}"})
    pub2 = client.get("/api/jobs")
    assert any(j["id"] == created["id"] for j in pub2.json())


def test_candidate_cannot_create_job(client):
    r = client.post("/api/auth/register", json={
        "email": "c@example.com", "password": "password", "name": "C", "role": "candidate"
    })
    j = client.post("/api/jobs", json={"title": "X", "team": "t", "location": "l", "seniority": "j",
        "required_skills": [], "nice_to_have": [], "min_years": 0, "education": "none", "narrative": "n"},
        headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert j.status_code == 403
```

- [ ] **Step 2: pytest fail (404)**
- [ ] **Step 3: Implement `generate_jd` as pure template (no LLM)**

Markdown sections exactly: Title, Team, Location, Seniority, Role summary, Required skills, Nice to have, Experience, Education, How to apply (`{public_base_url}/jobs/{id}`).

Routes: POST/PATCH `/api/jobs`, GET `/api/jobs` (if no user or candidate: only `open` and omit HR-only fields; HR: all), POST publish/close, GET export.md (text/markdown), GET export.pdf (reportlab or weasyprint; reportlab is in requirements).

- [ ] **Step 4: tests pass**
- [ ] **Step 5: Commit** `feat: job descriptions and internal board publish`

---

### Task 5: Apply, resume storage, duplicate detection

**Files:**
- Create: `backend/app/modules/candidates/schemas.py`
- Create: `backend/app/modules/candidates/service.py`
- Create: `backend/app/modules/candidates/router.py`
- Create: `backend/tests/test_apply.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `Job`, `User`, `Application`, auth register helper
- Produces: `POST /api/jobs/{id}/apply` multipart `resume` + `name` + `email` + `password` (if new); `GET /api/applications/{id}/resume`

- [ ] **Step 1: Failing tests**

```python
from io import BytesIO

def test_apply_creates_candidate_and_application(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    token = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    }).json()["token"]
    job = client.post("/api/jobs", json={
        "title": "X", "team": "T", "location": "L", "seniority": "j",
        "required_skills": ["python"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "n",
    }, headers={"Authorization": f"Bearer {token}"}).json()
    client.post(f"/api/jobs/{job['id']}/publish", headers={"Authorization": f"Bearer {token}"})
    files = {"resume": ("cv.txt", BytesIO(b"python developer with 4 years"), "text/plain")}
    r = client.post(f"/api/jobs/{job['id']}/apply", data={
        "email": "ada@example.com", "password": "password", "name": "Ada"
    }, files=files)
    assert r.status_code == 200
    assert r.json()["status"] in ("applied", "screened")


def test_duplicate_apply_409(client, tmp_path, monkeypatch):
    # same as above twice
    ...
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "duplicate_application"
```

Fill the second test by repeating apply.

Reject non txt/pdf/docx with 415.

- [ ] **Step 2: fail**
- [ ] **Step 3: implement apply**

If email exists, require password match (or if already logged in as that user, skip). If new, create candidate. Save file under `resume_dir/{application_id}/cv.txt`. Unique constraint on (job_id, candidate_id). Apply only if job `open`.

Do not implement scoring yet; status stays `applied` unless Task 6 is combined. Prefer calling `screening.score_application` if the function exists, else leave applied. In this task, stub `score_application` as no-op imported in Task 6.

- [ ] **Step 4: pass**
- [ ] **Step 5: Commit** `feat: public job apply and resume upload`

---

### Task 6: Resume parse and keyword screening

**Files:**
- Create: `backend/app/modules/screening/parse.py`
- Create: `backend/app/modules/screening/score.py`
- Create: `backend/app/modules/screening/service.py`
- Create: `backend/tests/test_screening.py`
- Modify: apply flow to call `run_screening(db, application)`

**Interfaces:**
- Consumes: application.parsed text, job skills/years/education
- Produces: `parse_resume(path: str) -> str`; `keyword_score(text: str, job: Job) -> tuple[float, dict]`; `run_screening(db, application) -> Application`

- [ ] **Step 1: Failing unit tests (no HTTP)**

```python
from types import SimpleNamespace
from app.modules.screening.score import keyword_score, infer_years, infer_education


def test_all_skills_hit():
    job = SimpleNamespace(required_skills=["python", "sql"], min_years=0, education="none", screen_threshold=0.6)
    score, breakdown = keyword_score("python and sql engineer", job)
    assert breakdown["skills"] == 1.0
    assert score >= 0.6


def test_years_ratio():
    job = SimpleNamespace(required_skills=[], min_years=4, education="none")
    score, breakdown = keyword_score("2 years of work", job)
    assert breakdown["years"] == 0.5


def test_education_rank():
    job = SimpleNamespace(required_skills=[], min_years=0, education="master")
    _, b = keyword_score("phd in cs", job)
    assert b["education"] == 1.0
    _, b2 = keyword_score("bachelor of arts", job)
    assert b2["education"] == 0.0


def test_threshold_promotes(client):
    # apply with text containing all required skills -> status screened
    ...


def test_below_threshold_stays_applied(client):
    ...
```

Years: regex `(\d+)\+?\s+years`, date ranges ` (19|20)\d{2}\s*[-–]\s*((19|20)\d{2}|present|now) `, cap 40.

Education keywords: phd/doctorate, master/msc/mba, bachelor/bsc/ba/bs.

- [ ] **Step 2: fail**
- [ ] **Step 3: implement parse.py** (pypdf, python-docx, utf-8 txt), score.py, service.py that writes encrypted parsed_text, scores, sets status screened if `keyword_score >= job.screen_threshold`. Empty parse sets `parse_error`. `POST /api/applications/{id}/parsed-text` HR-only retries.

LLM **not** in this task; `run_screening` may call `maybe_llm_rank` if imported, but implement `maybe_llm_rank` as empty function returning None.

- [ ] **Step 4: pass**
- [ ] **Step 5: Commit** `feat: keyword resume screening`

---

### Task 7: Pipeline transitions and HR override

**Files:**
- Create: `backend/app/modules/pipeline.py`
- Modify: `backend/app/modules/candidates/router.py`
- Create: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: Application.status
- Produces: `transition(app, new_status: str, *, has_feedback: bool, has_interview: bool) -> None` raises HTTP 409; `POST /api/applications/{id}/override`

Allowed map from spec section 13. Override pass: if status applied -> screened. Override fail: applied/screened -> rejected and enqueue rejection mail (call `mail.send_template` — if mail module missing, write message row inline then move mail to Task 8). Prefer implementing mail send in Task 8 and having override call `mail.send_rejection` which can be a no-op stub that Task 8 fills.

For this task, override fail sets rejected; tests for rejection **message** wait for Task 8 except a unit test on `transition`.

```python
from app.modules.pipeline import transition, IllegalTransition
import pytest

def test_illegal_offer_from_applied():
    with pytest.raises(IllegalTransition):
        transition("applied", "offer", has_feedback=False, has_interview=False)
```

- [ ] Implement `IllegalTransition` with `.code`
- [ ] Commit `feat: application pipeline transitions`

---

### Task 8: In-app mail templates and inbox API

**Files:**
- Create: `backend/app/modules/mail/templates.py`
- Create: `backend/app/modules/mail/service.py`
- Create: `backend/app/modules/mail/router.py`
- Create: `backend/tests/test_mail.py`

**Interfaces:**
- Produces: `send_template(db, *, to_user_id, template_key, context: dict, related_type, related_id) -> Message`; GET `/api/messages`; POST `/api/messages/{id}/read`; POST `/api/messages/{id}/retry-smtp` (no-op smtp until Task 12)

Templates:

- interview_invite subject `Interview for {job_title}`; body includes datetime and confirm path `/interviews/{id}`
- offer_letter subject `Offer: {job_title}`; body includes “to be confirmed”, accept path
- rejection subject `Update on {job_title}`; polite decline and “please apply again”

SMTP: `service.py` tries `_try_smtp` only if `smtp_host` non-empty; Task 12 fills real SMTP. For now `_try_smtp` returns immediately if host empty.

Wire override fail and (later) offer/reject to `send_template`.

Tests: screen-out reject creates rejection message without feedback.

- [ ] Commit `feat: in-app recruitment messages`

---

### Task 9: Local calendar, weekend rule, interviews

**Files:**
- Create: `backend/app/modules/calendar/service.py`
- Create: `backend/app/modules/calendar/router.py`
- Create: `backend/tests/test_calendar.py`

**Interfaces:**
- Produces: `assert_weekday(start_at, timezone)`; `list_open_slots(db, hr_user_id, start, end)`; interview CRUD routes; hours and blocks routes

- [ ] **Step 1: Tests**

```python
from datetime import datetime, timezone
from app.modules.calendar.service import assert_weekday, WeekendNotAllowed
import pytest

def test_saturday_rejected():
    # 2026-09-05 is Saturday
    with pytest.raises(WeekendNotAllowed):
        assert_weekday(datetime(2026, 9, 5, 15, 0, tzinfo=timezone.utc), "UTC")

def test_friday_ok():
    assert_weekday(datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc), "UTC")
```

HTTP: create interview on Saturday -> 409 `weekend_not_allowed`. Default slot 45 minutes. Overlap -> `slot_conflict`. Creating interview from screened sets application status `interview` and sends `interview_invite` to HR and candidate.

Default hours Mon–Fri 09:00–17:00 if none stored.

Google not in this task; `source='local'`.

- [ ] Commit `feat: weekday interview scheduling`

---

### Task 10: Feedback, offer, reject, accept, decline, withdraw

**Files:**
- Create: `backend/app/modules/feedback/service.py`
- Create: `backend/app/modules/feedback/router.py`
- Modify: `backend/tests/test_pipeline.py`

**Interfaces:**
- Produces: POST `/api/feedback`; POST offer/reject/accept-offer/decline-offer/withdraw

Rules: offer requires latest interview confirmed or completed **and** feedback row. Reject from interview requires feedback. Reject from applied/screened does not. Accept -> hired. Decline -> rejected. Withdraw from any pre-hire -> withdrawn.

Tests from spec 17.

- [ ] Commit `feat: offers rejections and interview feedback`

---

### Task 11: Optional SMTP

**Files:**
- Modify: `backend/app/modules/mail/service.py`
- Modify: `backend/tests/test_mail.py`

Use `smtplib.SMTP` STARTTLS when `smtp_host` set. Catch errors into `smtp_error`. Retry endpoint calls `_try_smtp` again.

Test with `unittest.mock.patch("smtplib.SMTP")`. Missing host: message still stored, `smtp_sent_at` null.

- [ ] Commit `feat: optional SMTP delivery for inbox messages`

---

### Task 12: Optional Google Calendar OAuth

**Files:**
- Create: `backend/app/modules/calendar/google.py`
- Modify: `backend/app/modules/calendar/router.py`
- Modify: `backend/app/modules/calendar/service.py`

Routes: GET connect (redirect to Google), GET callback (store encrypted refresh token), POST disconnect (clear token).

If `google_client_id` empty, connect returns 400 `{code: "google_not_configured"}` and slot listing uses local hours.

If token present, free/busy via Google; on confirm insert event; on cancel delete event. On Google API error, fall back to local and include `warning: google_unavailable` in JSON.

Do not implement a live OAuth test; mock httpx.

- [ ] Commit `feat: optional Google Calendar freebusy and events`

---

### Task 13: Optional LLM ranking

**Files:**
- Create: `backend/app/modules/screening/llm.py`
- Modify: `backend/app/modules/screening/service.py`
- Modify: `backend/tests/test_screening.py`

`maybe_llm_rank(text, job) -> tuple[int, str] | None`. If `user_llm_api_key` empty, return None. Else POST `{base}/chat/completions` with model, timeout 20s, parse integer 0–100 and one-sentence rationale. Failure -> None.

Never import or read `MCAI_LLM_*`.

- [ ] Commit `feat: optional LLM resume ranking`

---

### Task 14: GDPR export/delete, audit log, retention

**Files:**
- Create: `backend/app/modules/audit.py`
- Modify: `backend/app/modules/candidates/router.py`
- Create: `backend/tests/test_gdpr.py`

`log_action(db, actor_id, action, entity_type, entity_id)`.

GET `/api/me/export` candidate JSON: profile, applications, messages, interviews. GET `/api/candidates/{id}/export` HR.

DELETE `/api/me`: set deleted_at, replace email/name/phone with `deleted:{id}` encrypted, drop resume serving (set resume_path empty), keep scores without raw parsed_text (clear parsed_text_enc).

Tests: export only own applications; delete anonymizes.

Audit on login, apply, status change, mail send, export, delete.

- [ ] Commit `feat: candidate data export and deletion`

---

### Task 15: Frontend scaffold, auth, proxy, allowedHosts

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/style.css`
- Create: `frontend/src/api.js`
- Create: `frontend/src/router.js`
- Create: `frontend/src/stores/auth.js`
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/views/RegisterView.vue`
- Create: `frontend/src/components/AppShell.vue`

`vite.config.ts`:

```ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: [".monkeycode-ai.live"],
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
```

`api.js` attaches `Authorization: Bearer` from `localStorage.ats_token`. Login/register save token and user.

Router: `/login`, `/register`, `/` public jobs, HR routes under `/hr`, candidate under `/me`. Navigation guards by role.

Dependencies: `vue`, `vue-router`, `vite`, `@vitejs/plugin-vue`, `vitest`, `@vue/test-utils`.

- [ ] `cd frontend && npm install`
- [ ] Commit `feat: Vue app shell and auth screens`

---

### Task 16: Frontend public board and apply form

**Files:**
- Create: `frontend/src/views/PublicJobsView.vue`
- Create: `frontend/src/views/PublicJobDetailView.vue`
- Create: `frontend/src/__tests__/ApplyForm.spec.js`

Apply form: name, email, password if logged out, file input accept `.pdf,.docx,.txt`. Client validation before submit.

Vitest: missing file shows error; weekend not involved here.

- [ ] Commit `feat: public careers board and apply form`

---

### Task 17: HR jobs, dashboard, pipeline board

**Files:**
- Create: `frontend/src/views/HrDashboard.vue`
- Create: `frontend/src/views/JobsListView.vue`
- Create: `frontend/src/views/JobEditView.vue`
- Create: `frontend/src/views/PipelineView.vue`
- Create: `frontend/src/views/ApplicationDetailView.vue`
- Create: `frontend/src/components/PipelineBoard.vue`
- Create: `frontend/src/__tests__/PipelineBoard.spec.js`

PipelineBoard columns: Applied, Screened, Interview, Offer, Rejected. Hired/Withdrawn as tabs.

Vitest mounts board with fixture applications and asserts five column headers.

Job edit includes skills as comma-separated, generate/preview jd_markdown, publish, export links.

- [ ] Commit `feat: HR jobs and pipeline UI`

---

### Task 18: Calendar UI, slot picker, inbox, settings

**Files:**
- Create: `frontend/src/views/CalendarView.vue`
- Create: `frontend/src/views/InboxView.vue`
- Create: `frontend/src/views/SettingsView.vue`
- Create: `frontend/src/views/CandidateDashboard.vue`
- Create: `frontend/src/views/CandidateApplicationView.vue`
- Create: `frontend/src/components/SlotPicker.vue`
- Create: `frontend/src/components/StatusBanner.vue`
- Create: `frontend/src/__tests__/SlotPicker.spec.js`

SlotPicker: given a list of ISO datetimes, disable any Saturday/Sunday in HR timezone; emit selected slot.

Settings: show booleans `smtp_configured`, `google_configured`, `llm_configured` from `GET /api/auth/me` extra `integrations` object — add that field in backend `me` payload this task if missing (`bool(settings.smtp_host)` etc). Never show secrets.

Banners when an action needs Google/SMTP/LLM and it is missing.

- [ ] Commit `feat: calendar inbox and candidate portal UI`

---

### Task 19: Seed script, README, run wiring

**Files:**
- Create: `backend/scripts/seed.py`
- Create: `README.md`
- Modify: `.env.example` if needed

Seed: HR `hr@example.com` / `password`; two open jobs (Backend Engineer, Product Designer); five candidates mixed applied/screened/interview; one unread interview_invite.

README: generate Fernet key, copy `.env.example` to `backend/.env`, `pip install --break-system-packages -r backend/requirements.txt`, `PYTHONPATH=backend` uvicorn `app.main:app --host 0.0.0.0 --port 8000`, `cd frontend && npm install && npm run dev`, seed command.

- [ ] Run backend tests full suite
- [ ] Run `cd frontend && npx vitest run`
- [ ] Commit `chore: seed data and README`

---

## Spec coverage checklist

| Spec section | Task |
| --- | --- |
| 5 Architecture, secrets, degraded mode | 1, 11–13 |
| 6 Frontend surfaces | 15–18 |
| 7 Modules | 3–14 |
| 8 Data model | 2 |
| 9 JD generation / export | 4 |
| 10 Screening + paste retry | 6, 13 |
| 11 Calendar weekday + Google fallback | 9, 12 |
| 12 Mail templates + SMTP | 8, 11 |
| 13 Pipeline | 7, 10 |
| 14 Errors | throughout |
| 15 Security GDPR | 1, 3, 14 |
| 16 API | 3–14 |
| 17 Tests + seed | each task + 19 |
| 18 Layout | all |
| allowedHosts + /api proxy | 15 |

## Placeholder / consistency notes

- Function names locked: `generate_jd`, `run_screening`, `keyword_score`, `send_template`, `assert_weekday`, `transition`, `maybe_llm_rank`, `log_action`.
- Status strings and 409 codes match the spec exactly.
- No LinkedIn/Indeed adapters.

---
