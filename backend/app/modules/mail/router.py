from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crypto import decrypt_str
from app.db import get_db
from app.deps import get_current_user, require_hr
from app.models import Message, User
from app.modules.mail.service import retry_smtp

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _ser(m: Message) -> dict:
    return {
        "id": m.id,
        "template_key": m.template_key,
        "subject": m.subject,
        "body": m.body,
        "related_type": m.related_type,
        "related_id": m.related_id,
        "smtp_sent_at": m.smtp_sent_at.isoformat() if m.smtp_sent_at else None,
        "smtp_error": m.smtp_error,
        "read_at": m.read_at.isoformat() if m.read_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("")
def list_messages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Message)
        .filter(Message.to_user_id == user.id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return [_ser(m) for m in rows]


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Message).filter(Message.to_user_id == user.id, Message.read_at.is_(None)).count()
    return {"unread": n}


@router.post("/{message_id}/read")
def mark_read(message_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Message).filter(Message.id == message_id, Message.to_user_id == user.id).first()
    if m is None:
        raise HTTPException(status_code=404, detail="Not found")
    m.read_at = datetime.now(timezone.utc)
    db.commit()
    return _ser(m)


@router.post("/{message_id}/retry-smtp")
def retry(message_id: str, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    m = db.query(Message).filter(Message.id == message_id).first()
    if m is None:
        raise HTTPException(status_code=404, detail="Not found")
    target = db.query(User).filter(User.id == m.to_user_id).first()
    email = decrypt_str(target.email_enc) if target else ""
    retry_smtp(db, m, email)
    return _ser(m)
