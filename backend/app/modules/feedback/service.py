from sqlalchemy.orm import Session

from app.models import Feedback, Interview


def create_feedback(db: Session, interview: Interview, hr_id: str, rating: int, notes: str) -> Feedback:
    existing = db.query(Feedback).filter(Feedback.interview_id == interview.id).first()
    if existing:
        existing.rating = rating
        existing.notes = notes
        existing.hr_id = hr_id
        db.commit()
        db.refresh(existing)
        return existing
    row = Feedback(interview_id=interview.id, hr_id=hr_id, rating=rating, notes=notes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
