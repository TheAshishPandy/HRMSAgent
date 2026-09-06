import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet

os.environ.setdefault("JWT_SECRET", "seed-secret-at-least-32-chars-long!!")
if not os.environ.get("DATA_ENCRYPTION_KEY"):
    os.environ["DATA_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from app.config import get_settings
get_settings.cache_clear()

from app import db as dbmod
from app.db import Base, init_engine
from app import models  # noqa: F401
from app.crypto import decrypt_str, encrypt_str, hmac_email
from app.models import Employee, LeaveBalance, LeaveRequest, LeaveType, Organization, Payslip, PayrollRun, SalaryStructure, User, Job, Application, Interview, Message
from app.modules.payroll.router import compute
from app.modules.auth.service import hash_password, register
from app.modules.jobs.service import create_job, set_status
from app.themes import DEFAULT_MODULES
from app.modules.candidates.service import apply_to_job
from app.modules.calendar.service import create_interview


def main():
    Path("data/resumes").mkdir(parents=True, exist_ok=True)
    engine = init_engine()
    Base.metadata.create_all(engine)
    db = dbmod.SessionLocal()
    if db.query(User).filter(User.role == "hr").first():
        print("already seeded")
        return
    org = Organization(
        name="Northstar Labs",
        slug="northstar",
        theme_key="corporate_blue",
        layout_key="classic_sidebar",
        modules=list(DEFAULT_MODULES),
        status="active",
    )
    db.add(org)
    db.flush()
    admin = User(
        email_enc=encrypt_str("admin@example.com"),
        email_hash=hmac_email("admin@example.com"),
        password_hash=hash_password("password"),
        role="super_admin",
        name_enc=encrypt_str("Ada Admin"),
        timezone="UTC",
    )
    db.add(admin)
    db.commit()
    hr = register(db, "hr@example.com", "password", "Pat HR", "hr")
    hr.organization_id = org.id
    db.add(Employee(
        organization_id=org.id,
        user_id=hr.id,
        first_name="Pat",
        last_name="HR",
        email="hr@example.com",
        department="People",
        designation="Head of Talent",
        status="active",
        joining_date="2024-01-08",
    ))
    sam_user = User(
        email_enc=encrypt_str("sam.lee@example.com"),
        email_hash=hmac_email("sam.lee@example.com"),
        password_hash=hash_password("password"),
        role="employee",
        name_enc=encrypt_str("Sam Lee"),
        timezone="UTC",
        organization_id=org.id,
    )
    db.add(sam_user)
    db.flush()
    db.add(Employee(
        organization_id=org.id,
        user_id=sam_user.id,
        first_name="Sam",
        last_name="Lee",
        email="sam.lee@example.com",
        department="Engineering",
        designation="Staff Engineer",
        status="active",
        joining_date="2023-04-12",
    ))
    db.add(Employee(
        organization_id=org.id,
        first_name="Riley",
        last_name="Chen",
        email="riley.chen@example.com",
        department="Design",
        designation="Product Designer",
        status="active",
        joining_date="2025-02-03",
    ))
    db.flush()
    leave_defs = [("Annual", 20), ("Sick", 10), ("Casual", 5)]
    types = []
    for name, days in leave_defs:
        lt = LeaveType(organization_id=org.id, name=name, days_per_year=days, paid=1)
        db.add(lt)
        types.append(lt)
    db.flush()
    year = datetime.now(timezone.utc).year
    employees = db.query(Employee).filter(Employee.organization_id == org.id).all()
    for emp in employees:
        for lt in types:
            db.add(LeaveBalance(
                organization_id=org.id,
                employee_id=emp.id,
                leave_type_id=lt.id,
                year=year,
                remaining=float(lt.days_per_year),
            ))
    sam_emp = next(e for e in employees if e.email == "sam.lee@example.com")
    annual = next(t for t in types if t.name == "Annual")
    db.add(LeaveRequest(
        organization_id=org.id,
        employee_id=sam_emp.id,
        leave_type_id=annual.id,
        start_date="2026-09-14",
        end_date="2026-09-16",
        days=3,
        reason="Family visit",
        status="pending",
    ))
    salaries = {
        "hr@example.com": (90000, 20000, 5000, 10, 500),
        "sam.lee@example.com": (140000, 40000, 10000, 12, 800),
        "riley.chen@example.com": (110000, 30000, 8000, 10, 400),
    }
    structures = {}
    for emp in employees:
        nums = salaries.get(emp.email)
        if not nums:
            continue
        st = SalaryStructure(
            organization_id=org.id,
            employee_id=emp.id,
            basic=nums[0],
            hra=nums[1],
            allowance=nums[2],
            tax_percent=nums[3],
            other_deductions=nums[4],
        )
        db.add(st)
        structures[emp.id] = st
    db.flush()
    run = PayrollRun(organization_id=org.id, period="2026-08", status="processed")
    db.add(run)
    db.flush()
    for emp in employees:
        st = structures.get(emp.id)
        if st is None:
            continue
        calc = compute(st, bonus=0)
        db.add(Payslip(organization_id=org.id, run_id=run.id, employee_id=emp.id, period="2026-08", **calc))
    db.commit()
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
    }, organization_id=org.id)
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
    }, organization_id=org.id)
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
    print("seeded admin@example.com, hr@example.com, sam.lee@example.com / password")
    db.close()


if __name__ == "__main__":
    main()
