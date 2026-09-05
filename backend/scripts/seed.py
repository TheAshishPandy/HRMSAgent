import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet

os.environ.setdefault("JWT_SECRET", "seed-secret-at-least-32-chars-long!!")
if not os.environ.get("DATA_ENCRYPTION_KEY"):
    os.environ["DATA_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from app.config import get_settings
get_settings.cache_clear()

from app.db import Base, init_engine, SessionLocal
from app import models  # noqa: F401
from app.models import User, Job, Application, Interview, Message
from app.modules.auth.service import register
from app.modules.jobs.service import create_job, set_status
from app.modules.candidates.service import apply_to_job
from app.modules.calendar.service import create_interview
from app.crypto import decrypt_str


def main():
    Path("data/resumes").mkdir(parents=True, exist_ok=True)
    engine = init_engine()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    if db.query(User).filter(User.role == "hr").first():
        print("already seeded")
        return
    hr = register(db, "hr@example.com", "password", "Pat HR", "hr")
    j1 = create_job(db, hr.id, {
        "title": "Backend Engineer",
        "team": "Platform",
        "location": "Remote",
        "seniority": "mid",
        "required_skills": ["python", "sql"],
        "nice_to_have": ["aws"],
        "min_years": 3,
        "education": "bachelor",
        "narrative": "Build recruitment APIs and screening services.",
    })
    j2 = create_job(db, hr.id, {
        "title": "Product Designer",
        "team": "Design",
        "location": "Remote",
        "seniority": "mid",
        "required_skills": ["figma", "research"],
        "nice_to_have": ["illustration"],
        "min_years": 2,
        "education": "none",
        "narrative": "Shape the ATS experience for HR and candidates.",
    })
    set_status(db, j1, "open")
    set_status(db, j2, "open")
    resumes = [
        ("ada@example.com", "Ada Lovelace", b"python sql engineer with 6 years bachelor of science"),
        ("bob@example.com", "Bob Builder", b"retail associate"),
        ("cam@example.com", "Cam Chen", b"python developer 4 years"),
        ("dee@example.com", "Dee Patel", b"figma research designer 5 years"),
        ("eli@example.com", "Eli Ng", b"python sql kubernetes 8 years master"),
    ]
    apps = []
    for email, name, body in resumes:
        job = j1 if b"python" in body or b"retail" in body else j2
        if email.startswith("dee"):
            job = j2
        app = apply_to_job(
            db, job, email=email, password="password", name=name,
            filename="cv.txt", content=body, current_user=None,
        )
        apps.append(app)
    screened = next(a for a in apps if a.status == "screened")
    start = datetime.now(timezone.utc) + timedelta(days=3)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    start = start.replace(hour=14, minute=0, second=0, microsecond=0)
    iv = create_interview(db, screened, start, start + timedelta(minutes=45), "UTC", hr.id)
    from app.modules.mail.service import send_template
    cand = db.query(User).filter(User.id == screened.candidate_id).first()
    send_template(
        db,
        to_user_id=screened.candidate_id,
        template_key="interview_invite",
        context={
            "job_title": j1.title,
            "candidate_name": decrypt_str(cand.name_enc),
            "datetime": start.isoformat(),
            "confirm_url": "/me/applications/" + screened.id,
            "body": "",
        },
        related_type="interview",
        related_id=iv.id,
        to_email=decrypt_str(cand.email_enc),
    )
    print("seeded hr@example.com / password")
    db.close()


if __name__ == "__main__":
    main()
