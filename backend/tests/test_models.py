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
