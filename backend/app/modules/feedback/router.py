from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_hr
from app.models import Interview, User
from app.modules.feedback.service import create_feedback

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    interview_id: str
    rating: int = Field(ge=1, le=5)
    notes: str = ""


@router.post("")
def post_feedback(body: FeedbackIn, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    iv = db.query(Interview).filter(Interview.id == body.interview_id).first()
    if iv is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    row = create_feedback(db, iv, user.id, body.rating, body.notes)
    return {
        "id": row.id,
        "interview_id": row.interview_id,
        "rating": row.rating,
        "notes": row.notes,
    }
