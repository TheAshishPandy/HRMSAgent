from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import decrypt_str, encrypt_str, hmac_email
from app.db import get_db
from app.deps import get_current_user, require_hr
from app.errors import conflict
from app.models import Application, Feedback, Interview, Job, Message, User
from app.modules.audit import log_action
from app.modules.candidates.schemas import OverrideIn, ParsedTextIn
from app.modules.candidates.service import apply_to_job, serialize_application
from app.modules.jobs.service import get_job, serialize_job
from app.modules.mail.service import send_template
from app.modules.pipeline import IllegalTransition, transition
from app.modules.screening.service import run_screening

jobs_apply = APIRouter(prefix="/api/jobs", tags=["apply"])
apps_router = APIRouter(prefix="/api/applications", tags=["applications"])
me_router = APIRouter(prefix="/api", tags=["me"])


def _optional_user(request: Request, db: Session) -> User | None:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    from fastapi.security import HTTPAuthorizationCredentials
    from app.deps import get_current_user as _gcu

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth.split(" ", 1)[1])
    try:
        return _gcu(creds, db)
    except HTTPException:
        return None


@jobs_apply.post("/{job_id}/apply")
async def apply(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    resume: UploadFile = File(...),
    email: str = Form(""),
    password: str = Form(""),
    name: str = Form(""),
):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    user = _optional_user(request, db)
    content = await resume.read()
    app = apply_to_job(
        db,
        job,
        email=email or (decrypt_str(user.email_enc) if user else ""),
        password=password,
        name=name or (decrypt_str(user.name_enc) if user else ""),
        filename=resume.filename or "resume.txt",
        content=content,
        current_user=user,
    )
    cand = db.query(User).filter(User.id == app.candidate_id).first()
    return serialize_application(app, job, cand, hr=False)


def _app_or_404(db: Session, app_id: str) -> Application:
    app = db.query(Application).filter(Application.id == app_id).first()
    if app is None:
        raise HTTPException(status_code=404, detail="Not found")
    return app


def _can_view(user: User, app: Application) -> bool:
    return user.role == "hr" or app.candidate_id == user.id


@apps_router.get("")
def list_apps(job_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Application)
    if user.role != "hr":
        q = q.filter(Application.candidate_id == user.id)
    if job_id:
        q = q.filter(Application.job_id == job_id)
    rows = q.order_by(Application.created_at.desc()).all()
    out = []
    for a in rows:
        job = db.query(Job).filter(Job.id == a.job_id).first()
        cand = db.query(User).filter(User.id == a.candidate_id).first()
        out.append(serialize_application(a, job, cand, hr=user.role == "hr"))
    return out


@apps_router.get("/{app_id}")
def get_app(app_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    if not _can_view(user, app):
        raise HTTPException(status_code=403, detail="Forbidden")
    job = db.query(Job).filter(Job.id == app.job_id).first()
    cand = db.query(User).filter(User.id == app.candidate_id).first()
    data = serialize_application(app, job, cand, hr=user.role == "hr")
    ivs = db.query(Interview).filter(Interview.application_id == app.id).all()
    data["interviews"] = [
        {
            "id": i.id,
            "start_at": i.start_at.isoformat(),
            "end_at": i.end_at.isoformat(),
            "status": i.status,
            "timezone": i.timezone,
        }
        for i in ivs
    ]
    if job:
        data["job"] = serialize_job(job, hr=user.role == "hr")
        data["hr_id"] = job.created_by
    return data


@apps_router.get("/{app_id}/resume")
def get_resume(app_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    if not _can_view(user, app):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not app.resume_path or not Path(app.resume_path).exists():
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(app.resume_path)


@apps_router.post("/{app_id}/override")
def override(app_id: str, body: OverrideIn, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    job = db.query(Job).filter(Job.id == app.job_id).first()
    cand = db.query(User).filter(User.id == app.candidate_id).first()
    if body.decision == "pass":
        if app.status == "applied":
            try:
                transition(app.status, "screened")
            except IllegalTransition as exc:
                raise conflict(exc.code, exc.message)
            app.status = "screened"
        app.hr_override = "pass"
    elif body.decision == "fail":
        try:
            transition(app.status, "rejected", has_feedback=False, has_interview=False)
        except IllegalTransition as exc:
            raise conflict(exc.code, exc.message)
        app.status = "rejected"
        app.hr_override = "fail"
        ctx = {
            "job_title": job.title if job else "",
            "candidate_name": decrypt_str(cand.name_enc) if cand else "",
            "body": "",
        }
        send_template(
            db,
            to_user_id=app.candidate_id,
            template_key="rejection",
            context=ctx,
            related_type="application",
            related_id=app.id,
            to_email=decrypt_str(cand.email_enc) if cand else "",
        )
    else:
        raise HTTPException(status_code=422, detail="decision must be pass or fail")
    db.commit()
    db.refresh(app)
    log_action(db, user.id, "status_change", "application", app.id, commit=True)
    return serialize_application(app, job, cand, hr=True)


@apps_router.post("/{app_id}/parsed-text")
def paste_text(app_id: str, body: ParsedTextIn, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    app.parsed_text_enc = encrypt_str(body.text)
    app.parse_error = None
    db.commit()
    run_screening(db, app)
    job = db.query(Job).filter(Job.id == app.job_id).first()
    cand = db.query(User).filter(User.id == app.candidate_id).first()
    return serialize_application(app, job, cand, hr=True)


def _latest_interview(db: Session, app_id: str) -> Interview | None:
    return (
        db.query(Interview)
        .filter(Interview.application_id == app_id, Interview.status != "cancelled")
        .order_by(Interview.created_at.desc())
        .first()
    )


def _has_feedback(db: Session, iv: Interview | None) -> bool:
    if iv is None:
        return False
    return db.query(Feedback).filter(Feedback.interview_id == iv.id).first() is not None


@apps_router.post("/{app_id}/offer")
def send_offer(app_id: str, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    job = db.query(Job).filter(Job.id == app.job_id).first()
    cand = db.query(User).filter(User.id == app.candidate_id).first()
    iv = _latest_interview(db, app.id)
    has_fb = _has_feedback(db, iv)
    try:
        transition(app.status, "offer", has_feedback=has_fb, has_interview=iv is not None)
    except IllegalTransition as exc:
        raise conflict(exc.code, exc.message)
    app.status = "offer"
    db.commit()
    ctx = {
        "job_title": job.title if job else "",
        "candidate_name": decrypt_str(cand.name_enc) if cand else "",
        "accept_url": f"{get_settings().public_base_url}/me/applications/{app.id}",
        "decline_url": f"{get_settings().public_base_url}/me/applications/{app.id}",
        "body": "",
    }
    send_template(
        db,
        to_user_id=app.candidate_id,
        template_key="offer_letter",
        context=ctx,
        related_type="application",
        related_id=app.id,
        to_email=decrypt_str(cand.email_enc) if cand else "",
    )
    log_action(db, user.id, "status_change", "application", app.id, commit=True)
    return serialize_application(app, job, cand, hr=True)


@apps_router.post("/{app_id}/reject")
def reject(app_id: str, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    job = db.query(Job).filter(Job.id == app.job_id).first()
    cand = db.query(User).filter(User.id == app.candidate_id).first()
    iv = _latest_interview(db, app.id)
    has_fb = _has_feedback(db, iv)
    try:
        transition(
            app.status,
            "rejected",
            has_feedback=has_fb,
            has_interview=iv is not None,
        )
    except IllegalTransition as exc:
        raise conflict(exc.code, exc.message)
    app.status = "rejected"
    db.commit()
    ctx = {
        "job_title": job.title if job else "",
        "candidate_name": decrypt_str(cand.name_enc) if cand else "",
        "body": "",
    }
    send_template(
        db,
        to_user_id=app.candidate_id,
        template_key="rejection",
        context=ctx,
        related_type="application",
        related_id=app.id,
        to_email=decrypt_str(cand.email_enc) if cand else "",
    )
    log_action(db, user.id, "status_change", "application", app.id, commit=True)
    return serialize_application(app, job, cand, hr=True)


@apps_router.post("/{app_id}/accept-offer")
def accept_offer(app_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    if app.candidate_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        transition(app.status, "hired")
    except IllegalTransition as exc:
        raise conflict(exc.code, exc.message)
    app.status = "hired"
    db.commit()
    log_action(db, user.id, "status_change", "application", app.id, commit=True)
    job = db.query(Job).filter(Job.id == app.job_id).first()
    return serialize_application(app, job, user, hr=False)


@apps_router.post("/{app_id}/decline-offer")
def decline_offer(app_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    if app.candidate_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        transition(app.status, "rejected")
    except IllegalTransition as exc:
        raise conflict(exc.code, exc.message)
    app.status = "rejected"
    db.commit()
    log_action(db, user.id, "status_change", "application", app.id, commit=True)
    job = db.query(Job).filter(Job.id == app.job_id).first()
    return serialize_application(app, job, user, hr=False)


@apps_router.post("/{app_id}/withdraw")
def withdraw(app_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _app_or_404(db, app_id)
    if app.candidate_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        transition(app.status, "withdrawn")
    except IllegalTransition as exc:
        raise conflict(exc.code, exc.message)
    app.status = "withdrawn"
    db.commit()
    log_action(db, user.id, "status_change", "application", app.id, commit=True)
    job = db.query(Job).filter(Job.id == app.job_id).first()
    return serialize_application(app, job, user, hr=False)


def _export_payload(db: Session, user: User) -> dict:
    apps = db.query(Application).filter(Application.candidate_id == user.id).all()
    messages = db.query(Message).filter(Message.to_user_id == user.id).all()
    app_ids = [a.id for a in apps]
    interviews = db.query(Interview).filter(Interview.application_id.in_(app_ids)).all() if app_ids else []
    return {
        "profile": {
            "id": user.id,
            "email": decrypt_str(user.email_enc),
            "name": decrypt_str(user.name_enc),
            "role": user.role,
        },
        "applications": [
            {
                "id": a.id,
                "job_id": a.job_id,
                "status": a.status,
                "keyword_score": a.keyword_score,
                "llm_score": a.llm_score,
            }
            for a in apps
        ],
        "messages": [{"id": m.id, "subject": m.subject, "body": m.body} for m in messages],
        "interviews": [
            {"id": i.id, "start_at": i.start_at.isoformat(), "status": i.status}
            for i in interviews
        ],
    }


@me_router.get("/me/export")
def me_export(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_action(db, user.id, "export", "user", user.id, commit=True)
    return _export_payload(db, user)


@me_router.delete("/me")
def me_delete(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime, timezone

    marker = f"deleted:{user.id}"
    user.email_enc = encrypt_str(marker)
    user.name_enc = encrypt_str(marker)
    user.phone_enc = encrypt_str(marker)
    user.email_hash = hmac_email(marker)
    user.deleted_at = datetime.now(timezone.utc)
    apps = db.query(Application).filter(Application.candidate_id == user.id).all()
    for a in apps:
        a.resume_path = ""
        a.parsed_text_enc = None
    db.commit()
    log_action(db, user.id, "delete", "user", user.id, commit=True)
    return {"ok": True}


@me_router.get("/candidates/{candidate_id}/export")
def hr_export(candidate_id: str, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    cand = db.query(User).filter(User.id == candidate_id).first()
    if cand is None:
        raise HTTPException(status_code=404, detail="Not found")
    log_action(db, user.id, "export", "user", cand.id, commit=True)
    return _export_payload(db, cand)


@me_router.get("/hr/dashboard")
def hr_dashboard(user: User = Depends(require_hr), db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    apps = db.query(Application).all()
    counts = defaultdict(int)
    for a in apps:
        counts[a.status] += 1
    from datetime import datetime, timezone, timedelta

    soon = datetime.now(timezone.utc) + timedelta(days=7)
    now = datetime.now(timezone.utc)
    upcoming = (
        db.query(Interview)
        .filter(Interview.status.in_(["proposed", "confirmed"]), Interview.start_at >= now, Interview.start_at <= soon)
        .count()
    )
    unread = (
        db.query(Message)
        .filter(Message.to_user_id == user.id, Message.read_at.is_(None))
        .count()
    )
    return {
        "open_jobs": sum(1 for j in jobs if j.status == "open"),
        "pipeline": dict(counts),
        "upcoming_interviews": upcoming,
        "unread": unread,
    }
