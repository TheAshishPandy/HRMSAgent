from datetime import date, timedelta

from app.models import (
    Application,
    Employee,
    Interview,
    Job,
    Message,
    Onboarding,
    OnboardingTask,
    User,
)
from tests.test_tenants import _auth, _org, _user


def _job(db, hr_id, org_id, title="Backend Engineer"):
    j = Job(
        created_by=hr_id, organization_id=org_id, title=title, team="Platform",
        location="Remote", seniority="mid", required_skills=["python"], nice_to_have=[],
        min_years=3, education="bachelor", narrative="n", jd_markdown="# jd", status="open",
    )
    db.add(j)
    db.commit()
    db.refresh(j)
    return j


def _hired_app(db, cand, hr_id, org_id):
    job = _job(db, hr_id, org_id)
    app = Application(job_id=job.id, candidate_id=cand.id, status="hired")
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def test_hr_lists_eligible_hires(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hrt = _user(db, "hr@example.com", "hr", org.id)
    cand, _ = _user(db, "ada@example.com", "candidate", org.id)
    _hired_app(db, cand, hr_user.id, org.id)
    r = client.get("/api/onboarding/eligible", headers=_auth(hrt))
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["candidate_name"] == "ada@example.com"


def test_onboard_creates_employee_and_checklist(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hrt = _user(db, "hr@example.com", "hr", org.id)
    cand, ct = _user(db, "ada@example.com", "candidate", org.id)
    app = _hired_app(db, cand, hr_user.id, org.id)
    start = (date.today() + timedelta(days=7)).isoformat()
    r = client.post("/api/onboarding", json={
        "application_id": app.id,
        "department": "Engineering",
        "designation": "Software Engineer",
        "joining_date": start,
    }, headers=_auth(hrt))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "active"
    assert len(body["tasks"]) >= 3
    emp = db.query(Employee).filter(Employee.email == "ada@example.com").first()
    assert emp is not None
    assert emp.department == "Engineering"
    db.refresh(cand)
    assert cand.role == "employee"
    msg = db.query(Message).filter(Message.to_user_id == cand.id).first()
    assert msg is not None and "onboard" in msg.body.lower()
    db.refresh(app)
    assert app.status == "hired"


def test_duplicate_onboarding_conflicts(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hrt = _user(db, "hr@example.com", "hr", org.id)
    cand, _ = _user(db, "ada@example.com", "candidate", org.id)
    app = _hired_app(db, cand, hr_user.id, org.id)
    payload = {"application_id": app.id, "department": "Eng", "designation": "SWE",
               "joining_date": "2026-10-01"}
    first = client.post("/api/onboarding", json=payload, headers=_auth(hrt))
    assert first.status_code == 200
    dup = client.post("/api/onboarding", json=payload, headers=_auth(hrt))
    assert dup.status_code == 409


def test_candidate_cannot_start_onboarding(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, _ = _user(db, "hr@example.com", "hr", org.id)
    cand, ct = _user(db, "ada@example.com", "candidate", org.id)
    app = _hired_app(db, cand, hr_user.id, org.id)
    r = client.post("/api/onboarding", json={
        "application_id": app.id, "department": "Eng", "designation": "SWE",
        "joining_date": "2026-10-01",
    }, headers=_auth(ct))
    assert r.status_code == 403


def test_employee_marks_task_complete(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hrt = _user(db, "hr@example.com", "hr", org.id)
    cand, ct = _user(db, "ada@example.com", "candidate", org.id)
    app = _hired_app(db, cand, hr_user.id, org.id)
    onboard = client.post("/api/onboarding", json={
        "application_id": app.id, "department": "Eng", "designation": "SWE",
        "joining_date": "2026-10-01",
    }, headers=_auth(hrt)).json()
    task_id = onboard["tasks"][0]["id"]
    r = client.post(f"/api/onboarding/tasks/{task_id}/complete", headers=_auth(ct))
    assert r.status_code == 200
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    assert task.completed == 1
    rec = db.query(Onboarding).filter(Onboarding.id == onboard["id"]).first()
    assert rec.completed_tasks >= 1


def test_employee_own_onboarding_progress(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hrt = _user(db, "hr@example.com", "hr", org.id)
    cand, ct = _user(db, "ada@example.com", "candidate", org.id)
    app = _hired_app(db, cand, hr_user.id, org.id)
    onboard = client.post("/api/onboarding", json={
        "application_id": app.id, "department": "Eng", "designation": "SWE",
        "joining_date": "2026-10-01",
    }, headers=_auth(hrt)).json()
    mine = client.get("/api/onboarding/me", headers=_auth(ct))
    assert mine.status_code == 200
    assert mine.json()["id"] == onboard["id"]


def test_offboard_employee(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hrt = _user(db, "hr@example.com", "hr", org.id)
    emp_user, et = _user(db, "sam@example.com", "employee", org.id)
    emp = Employee(
        organization_id=org.id, user_id=emp_user.id, first_name="Sam", last_name="Lee",
        email="sam@example.com", department="Eng", designation="IC", status="active",
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    r = client.post(f"/api/onboarding/employees/{emp.id}/offboard", json={
        "exit_date": "2026-11-01", "reason": "Resigned",
    }, headers=_auth(hrt))
    assert r.status_code == 200
    db.refresh(emp)
    assert emp.status == "inactive"
    assert emp.exit_date == "2026-11-01"
    msg = db.query(Message).filter(Message.to_user_id == emp_user.id).first()
    assert msg is not None


def test_hr_list_onboarding_records(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hrt = _user(db, "hr@example.com", "hr", org.id)
    cand, _ = _user(db, "ada@example.com", "candidate", org.id)
    _hired_app(db, cand, hr_user.id, org.id)
    client.post("/api/onboarding", json={
        "application_id": db.query(Application).first().id,
        "department": "Eng", "designation": "SWE", "joining_date": "2026-10-01",
    }, headers=_auth(hrt))
    r = client.get("/api/onboarding", headers=_auth(hrt))
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["tasks_total"] > 0
    assert "employee_name" in r.json()[0]


def test_unread_count(client, db):
    org = _org(db, "Org A", "org-a")
    emp_user, et = _user(db, "sam@example.com", "employee", org.id)
    client.get("/api/messages/unread-count", headers=_auth(et))
    db.add(Message(
        to_user_id=emp_user.id, template_key="generic", subject="Hi", body="Hello there",
    ))
    db.commit()
    r = client.get("/api/messages/unread-count", headers=_auth(et))
    assert r.status_code == 200
    assert r.json()["unread"] == 1
