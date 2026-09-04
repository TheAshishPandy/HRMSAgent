from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Job
from app.modules.jobs.jd import generate_jd

HR_FIELDS = (
    "id",
    "created_by",
    "title",
    "team",
    "location",
    "seniority",
    "required_skills",
    "nice_to_have",
    "min_years",
    "education",
    "narrative",
    "jd_markdown",
    "status",
    "screen_threshold",
    "created_at",
    "updated_at",
)

PUBLIC_FIELDS = (
    "id",
    "title",
    "team",
    "location",
    "seniority",
    "required_skills",
    "nice_to_have",
    "min_years",
    "education",
    "jd_markdown",
    "status",
)


def _lower_skills(skills: list | None) -> list:
    if not skills:
        return []
    return [s.lower() for s in skills]


def apply_url_for(job_id: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/jobs/{job_id}"


def _fields_for_jd(job: Job) -> dict:
    return {
        "title": job.title,
        "team": job.team,
        "location": job.location,
        "seniority": job.seniority,
        "required_skills": job.required_skills,
        "nice_to_have": job.nice_to_have,
        "min_years": job.min_years,
        "education": job.education,
        "narrative": job.narrative,
    }


def serialize_job(job: Job, hr: bool) -> dict:
    keys = HR_FIELDS if hr else PUBLIC_FIELDS
    out = {}
    for k in keys:
        val = getattr(job, k)
        if isinstance(val, datetime):
            out[k] = val.isoformat()
        else:
            out[k] = val
    return out


def create_job(db: Session, user_id: str, data: dict) -> Job:
    job = Job(
        created_by=user_id,
        title=data["title"],
        team=data["team"],
        location=data["location"],
        seniority=data["seniority"],
        required_skills=_lower_skills(data.get("required_skills")),
        nice_to_have=_lower_skills(data.get("nice_to_have")),
        min_years=data["min_years"],
        education=data["education"],
        narrative=data["narrative"],
        jd_markdown="",
        status="draft",
        screen_threshold=data.get("screen_threshold") if data.get("screen_threshold") is not None else 0.6,
    )
    db.add(job)
    db.flush()
    job.jd_markdown = generate_jd(_fields_for_jd(job), apply_url_for(job.id))
    db.commit()
    db.refresh(job)
    return job


def list_jobs(db: Session, hr: bool) -> list[Job]:
    q = db.query(Job)
    if not hr:
        q = q.filter(Job.status == "open")
    return q.order_by(Job.created_at.desc()).all()


def get_job(db: Session, job_id: str) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()


def update_job(db: Session, job: Job, data: dict) -> Job:
    regen = False
    jd_override = data.pop("jd_markdown", None)
    for key, val in data.items():
        if val is None:
            continue
        if key in ("required_skills", "nice_to_have"):
            val = _lower_skills(val)
        setattr(job, key, val)
        if key != "screen_threshold":
            regen = True
    if jd_override is not None:
        job.jd_markdown = jd_override
    elif regen:
        job.jd_markdown = generate_jd(_fields_for_jd(job), apply_url_for(job.id))
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def set_status(db: Session, job: Job, status: str) -> Job:
    job.status = status
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job
