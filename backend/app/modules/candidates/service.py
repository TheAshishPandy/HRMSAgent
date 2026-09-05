import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import decrypt_str, encrypt_str, hmac_email
from app.errors import conflict
from app.models import Application, Job, User
from app.modules.auth.service import register, verify_password
from app.modules.audit import log_action
from app.modules.screening.service import run_screening

ALLOWED_EXT = {".txt", ".pdf", ".docx"}


def _safe_name(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return base or "resume.txt"


def serialize_application(app: Application, job: Job | None, candidate: User | None, hr: bool) -> dict:
    out = {
        "id": app.id,
        "job_id": app.job_id,
        "candidate_id": app.candidate_id,
        "status": app.status,
        "keyword_score": app.keyword_score,
        "score_breakdown": app.score_breakdown,
        "llm_score": app.llm_score,
        "llm_rationale": app.llm_rationale if hr else None,
        "hr_override": app.hr_override if hr else None,
        "parse_error": app.parse_error,
        "created_at": app.created_at.isoformat() if app.created_at else None,
    }
    if job is not None:
        out["job_title"] = job.title
    if candidate is not None:
        out["candidate_name"] = decrypt_str(candidate.name_enc)
        if hr:
            out["candidate_email"] = decrypt_str(candidate.email_enc)
    if hr:
        out["has_resume"] = bool(app.resume_path)
        if app.parsed_text_enc:
            try:
                out["parsed_text"] = decrypt_str(app.parsed_text_enc)
            except Exception:
                out["parsed_text"] = ""
    return out


def apply_to_job(
    db: Session,
    job: Job,
    *,
    email: str,
    password: str,
    name: str,
    filename: str,
    content: bytes,
    current_user: User | None,
) -> Application:
    if job.status != "open":
        raise conflict("job_closed", "Job is not open")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        from fastapi import HTTPException

        raise HTTPException(status_code=415, detail="Unsupported resume type")
    user = current_user
    if user is None:
        existing = (
            db.query(User)
            .filter(User.email_hash == hmac_email(email), User.deleted_at.is_(None))
            .first()
        )
        if existing:
            if not verify_password(password, existing.password_hash):
                from fastapi import HTTPException

                raise HTTPException(status_code=401, detail="Invalid credentials")
            user = existing
        else:
            user = register(db, email, password, name, "candidate")
    dup = (
        db.query(Application)
        .filter(Application.job_id == job.id, Application.candidate_id == user.id)
        .first()
    )
    if dup:
        raise conflict("duplicate_application", "Already applied")
    app = Application(
        job_id=job.id,
        candidate_id=user.id,
        status="applied",
        resume_path=None,
    )
    db.add(app)
    db.flush()
    dest_dir = Path(get_settings().resume_dir) / app.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / _safe_name(filename)
    dest.write_bytes(content)
    app.resume_path = str(dest)
    db.commit()
    db.refresh(app)
    log_action(db, user.id, "apply", "application", app.id, commit=True)
    return run_screening(db, app)
