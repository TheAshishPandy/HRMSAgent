from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import encrypt_str
from app.db import get_db
from app.deps import get_current_user, require_hr
from app.models import Application, CalendarBlock, Interview, Job, User
from app.modules.audit import log_action
from app.modules.calendar import google, service
from app.modules.mail.service import send_template

router = APIRouter(prefix="/api", tags=["calendar"])


class HoursIn(BaseModel):
    hours: list[dict]


class BlockIn(BaseModel):
    start_at: datetime
    end_at: datetime
    reason: str | None = None


class InterviewIn(BaseModel):
    application_id: str
    start_at: datetime
    end_at: datetime | None = None


def _iv_ser(iv: Interview) -> dict:
    return {
        "id": iv.id,
        "application_id": iv.application_id,
        "start_at": iv.start_at.isoformat(),
        "end_at": iv.end_at.isoformat(),
        "timezone": iv.timezone,
        "source": iv.source,
        "status": iv.status,
    }


@router.get("/calendar/slots")
def slots(
    hr_id: str = Query(...),
    from_: str = Query(alias="from"),
    to: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start = datetime.fromisoformat(from_.replace("Z", "+00:00"))
    end = datetime.fromisoformat(to.replace("Z", "+00:00"))
    cand = user.id if user.role == "candidate" else None
    return service.list_open_slots(db, hr_id, start, end, candidate_id=cand)


@router.get("/calendar/hours")
def hours_get(user: User = Depends(require_hr), db: Session = Depends(get_db)):
    return service.get_hours(db, user.id)


@router.put("/calendar/hours")
def hours_put(body: HoursIn, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    return service.set_hours(db, user.id, body.hours)


@router.get("/calendar/blocks")
def blocks_get(user: User = Depends(require_hr), db: Session = Depends(get_db)):
    rows = db.query(CalendarBlock).filter(CalendarBlock.hr_user_id == user.id).all()
    return [
        {
            "id": b.id,
            "start_at": b.start_at.isoformat(),
            "end_at": b.end_at.isoformat(),
            "reason": b.reason,
        }
        for b in rows
    ]


@router.post("/calendar/blocks")
def blocks_post(body: BlockIn, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    b = CalendarBlock(
        hr_user_id=user.id,
        start_at=body.start_at if body.start_at.tzinfo else body.start_at.replace(tzinfo=timezone.utc),
        end_at=body.end_at if body.end_at.tzinfo else body.end_at.replace(tzinfo=timezone.utc),
        reason=body.reason,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return {"id": b.id, "start_at": b.start_at.isoformat(), "end_at": b.end_at.isoformat(), "reason": b.reason}


@router.delete("/calendar/blocks/{block_id}")
def blocks_del(block_id: str, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    b = db.query(CalendarBlock).filter(CalendarBlock.id == block_id, CalendarBlock.hr_user_id == user.id).first()
    if b is None:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(b)
    db.commit()
    return {"ok": True}


def _notify_invite(db: Session, iv: Interview, application: Application, job: Job, hr: User):
    from app.crypto import decrypt_str as dec
    cand = db.query(User).filter(User.id == application.candidate_id).first()
    ctx = {
        "job_title": job.title,
        "candidate_name": dec(cand.name_enc) if cand else "",
        "datetime": iv.start_at.isoformat(),
        "confirm_url": f"{get_settings().public_base_url}/me/applications/{application.id}",
        "body": "",
    }
    if cand:
        send_template(
            db,
            to_user_id=cand.id,
            template_key="interview_invite",
            context=ctx,
            related_type="interview",
            related_id=iv.id,
            to_email=dec(cand.email_enc),
        )
    send_template(
        db,
        to_user_id=hr.id,
        template_key="interview_invite",
        context=ctx,
        related_type="interview",
        related_id=iv.id,
        to_email=dec(hr.email_enc),
    )


@router.post("/interviews")
def create_iv(body: InterviewIn, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == body.application_id).first()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    job = db.query(Job).filter(Job.id == app.job_id).first()
    end = body.end_at or (body.start_at + timedelta(minutes=45))
    iv = service.create_interview(db, app, body.start_at, end, user.timezone or "UTC", user.id)
    log_action(db, user.id, "status_change", "application", app.id, commit=True)
    _notify_invite(db, iv, app, job, user)
    return _iv_ser(iv)


@router.post("/interviews/{interview_id}/confirm")
def confirm_iv(interview_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    iv = db.query(Interview).filter(Interview.id == interview_id).first()
    if iv is None:
        raise HTTPException(status_code=404, detail="Not found")
    iv.status = "confirmed"
    db.commit()
    db.refresh(iv)
    return _iv_ser(iv)


@router.post("/interviews/{interview_id}/cancel")
def cancel_iv(interview_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    iv = db.query(Interview).filter(Interview.id == interview_id).first()
    if iv is None:
        raise HTTPException(status_code=404, detail="Not found")
    iv.status = "cancelled"
    db.commit()
    db.refresh(iv)
    return _iv_ser(iv)


@router.post("/interviews/{interview_id}/complete")
def complete_iv(interview_id: str, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    iv = db.query(Interview).filter(Interview.id == interview_id).first()
    if iv is None:
        raise HTTPException(status_code=404, detail="Not found")
    iv.status = "completed"
    db.commit()
    db.refresh(iv)
    return _iv_ser(iv)


@router.get("/calendar/google/connect")
def google_connect(user: User = Depends(require_hr)):
    if not google.configured():
        raise HTTPException(status_code=400, detail={"code": "google_not_configured", "message": "Google OAuth is not configured"})
    return RedirectResponse(google.auth_url(user.id))


@router.get("/calendar/google/callback")
def google_callback(code: str = "", state: str = "", db: Session = Depends(get_db)):
    token = google.exchange_code(code)
    user = db.query(User).filter(User.id == state).first()
    if user and token:
        user.google_refresh_token_enc = encrypt_str(token)
        db.commit()
    return RedirectResponse(get_settings().public_base_url + "/hr/calendar")


@router.post("/calendar/google/disconnect")
def google_disconnect(user: User = Depends(require_hr), db: Session = Depends(get_db)):
    user.google_refresh_token_enc = None
    db.commit()
    return {"ok": True}
