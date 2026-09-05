from sqlalchemy.orm import Session

from app.crypto import encrypt_str, decrypt_str
from app.models import Application, Job
from app.modules.screening.llm import maybe_llm_rank
from app.modules.screening.parse import parse_resume
from app.modules.screening.score import keyword_score


def run_screening(db: Session, application: Application) -> Application:
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if job is None:
        return application
    text = ""
    if application.parsed_text_enc:
        try:
            text = decrypt_str(application.parsed_text_enc)
        except Exception:
            text = ""
    if not text and application.resume_path:
        try:
            text = parse_resume(application.resume_path)
        except Exception as exc:
            application.parse_error = str(exc)
            db.commit()
            db.refresh(application)
            return application
    if not text.strip():
        application.parse_error = "empty_parse"
        db.commit()
        db.refresh(application)
        return application
    application.parsed_text_enc = encrypt_str(text)
    application.parse_error = None
    score, breakdown = keyword_score(text, job)
    application.keyword_score = score
    application.score_breakdown = breakdown
    if application.status == "applied" and score >= (job.screen_threshold or 0.6):
        application.status = "screened"
    ranked = maybe_llm_rank(text, job)
    if ranked is not None:
        application.llm_score = ranked[0]
        application.llm_rationale = ranked[1]
    db.commit()
    db.refresh(application)
    return application
