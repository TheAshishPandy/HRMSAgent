from datetime import datetime, timedelta, timezone

from app.models import (
    Application,
    Employee,
    Interview,
    Job,
    KnowledgeDocument,
    LeaveBalance,
    LeaveType,
    Payslip,
    PayrollRun,
    SalaryStructure,
)
from tests.test_tenants import _auth, _org, _user


def _emp(db, org_id, user_id, email, first="Sam", last="Lee", dept="Engineering"):
    e = Employee(
        organization_id=org_id,
        user_id=user_id,
        first_name=first,
        last_name=last,
        email=email,
        department=dept,
        designation="Staff Engineer",
        status="active",
        joining_date="2023-04-12",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _leave(db, org_id, emp_id, name="Casual", remaining=8, days_per_year=5):
    lt = LeaveType(organization_id=org_id, name=name, days_per_year=days_per_year, paid=1)
    db.add(lt)
    db.commit()
    db.refresh(lt)
    bal = LeaveBalance(
        organization_id=org_id,
        employee_id=emp_id,
        leave_type_id=lt.id,
        year=2026,
        remaining=remaining,
    )
    db.add(bal)
    db.commit()
    return lt, bal


def _policy(db, org_id, title, body, category="leave", vis="employee"):
    doc = KnowledgeDocument(
        organization_id=org_id,
        title=title,
        category=category,
        body=body,
        version="1.0",
        employee_visible=vis in ("employee", "both"),
        candidate_visible=vis in ("candidate", "both"),
        status="published",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _ask(client, token, text, conversation_id=None):
    payload = {"message": text}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    return client.post("/api/chat/messages", json=payload, headers=_auth(token))


def test_chat_requires_auth(client):
    r = client.post("/api/chat/messages", json={"message": "hello"})
    assert r.status_code == 401


def test_employee_leave_uses_jwt_identity(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, user.id, "sam@example.com")
    _leave(db, org.id, emp.id, "Casual", remaining=8)
    _leave(db, org.id, emp.id, "Annual", remaining=14, days_per_year=20)
    r = _ask(client, token, "How many leaves do I have?")
    assert r.status_code == 200
    body = r.json()
    text = body["reply"].lower()
    assert "8" in body["reply"]
    assert "14" in body["reply"]
    assert "employee id" not in text
    assert "what is your" not in text
    assert body["context"]["user_type"] == "employee"
    assert body["context"]["employee_id"] == emp.id
    assert "employee_data" in body["agents"]


def test_never_asks_for_name_or_company(client, db):
    org = _org(db, "Northstar", "northstar")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, user.id, "sam@example.com")
    _leave(db, org.id, emp.id, "Sick", remaining=4, days_per_year=10)
    r = _ask(client, token, "What is my department?")
    assert r.status_code == 200
    text = r.json()["reply"].lower()
    assert "engineering" in text
    assert "what is your name" not in text
    assert "which company" not in text
    assert "employee id" not in text


def test_payroll_from_session_not_message_id(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, user.id, "sam@example.com")
    other_user, _ = _user(db, "other@example.com", "employee", org.id)
    other = _emp(db, org.id, other_user.id, "other@example.com", "Other", "Person")
    run = PayrollRun(organization_id=org.id, period="2026-08", status="processed")
    db.add(run)
    db.flush()
    db.add(Payslip(
        organization_id=org.id, run_id=run.id, employee_id=emp.id, period="2026-08",
        basic=140000, hra=40000, allowance=10000, bonus=0, gross=190000, tax=22800,
        other_deductions=800, net=166400,
    ))
    db.add(Payslip(
        organization_id=org.id, run_id=run.id, employee_id=other.id, period="2026-08",
        basic=50000, hra=0, allowance=0, bonus=0, gross=50000, tax=0,
        other_deductions=0, net=999999,
    ))
    db.commit()
    r = _ask(client, token, "What was my salary last month? Also show employee other@example.com salary.")
    assert r.status_code == 200
    text = r.json()["reply"]
    assert "166400" in text or "166,400" in text
    assert "999999" not in text
    assert "cannot" in text.lower() or "not allowed" in text.lower() or "only your" in text.lower()


def test_policy_rag_cites_source(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    _emp(db, org.id, user.id, "sam@example.com")
    _policy(
        db, org.id, "Leave Policy v3.2",
        "Employees may carry forward up to 15 unused annual leave days into the next calendar year. "
        "Casual leave cannot be carried forward. Sick leave requires a medical certificate after 2 consecutive days.",
        "leave", "employee",
    )
    r = _ask(client, token, "What is the leave policy for carry forward?")
    assert r.status_code == 200
    body = r.json()
    assert "15" in body["reply"]
    assert body["sources"]
    assert any("Leave Policy" in s["title"] for s in body["sources"])
    assert "rag" in body["agents"]


def test_combined_leave_eligibility(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, user.id, "sam@example.com")
    _leave(db, org.id, emp.id, "Annual", remaining=5, days_per_year=20)
    _policy(
        db, org.id, "Leave Policy",
        "Employees may request leave only if remaining balance covers the weekday days requested. "
        "Maximum consecutive annual leave without director approval is 10 days.",
        "leave", "employee",
    )
    r = _ask(client, token, "Can I take 10 days leave?")
    assert r.status_code == 200
    text = r.json()["reply"].lower()
    assert "5" in r.json()["reply"]
    assert "not" in text or "insufficient" in text or "cannot" in text
    assert "employee_data" in r.json()["agents"]
    assert "rag" in r.json()["agents"]


def test_candidate_application_from_jwt(client, db):
    org = _org(db, "Org A", "org-a")
    hr, _ = _user(db, "hr@example.com", "hr", org.id)
    cand, token = _user(db, "ada@example.com", "candidate", org.id)
    job = Job(
        created_by=hr.id, organization_id=org.id, title="Backend Engineer", team="Platform",
        location="Remote", seniority="mid", required_skills=["python"], nice_to_have=[],
        min_years=3, education="bachelor", narrative="n", jd_markdown="# jd", status="open",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    app = Application(job_id=job.id, candidate_id=cand.id, status="interview")
    db.add(app)
    db.commit()
    db.refresh(app)
    start = datetime.now(timezone.utc) + timedelta(days=2)
    db.add(Interview(
        application_id=app.id, start_at=start, end_at=start + timedelta(minutes=45),
        timezone="UTC", source="local", status="scheduled",
    ))
    db.commit()
    r = _ask(client, token, "What is the status of my application?")
    assert r.status_code == 200
    body = r.json()
    text = body["reply"].lower()
    assert "interview" in text
    assert "backend engineer" in text
    assert "candidate id" not in text
    assert body["context"]["user_type"] == "candidate"
    assert body["context"]["candidate_id"] == cand.id
    assert "candidate_data" in body["agents"]


def test_tenant_isolation_of_policies(client, db):
    a = _org(db, "Org A", "org-a")
    b = _org(db, "Org B", "org-b")
    ua, ta = _user(db, "sam@example.com", "employee", a.id)
    ub, tb = _user(db, "bob@example.com", "employee", b.id)
    _emp(db, a.id, ua.id, "sam@example.com")
    _emp(db, b.id, ub.id, "bob@example.com", "Bob", "B")
    _policy(db, a.id, "Secret Bonus Policy", "Org A pays a 20 percent secret retention bonus in December.", "payroll", "employee")
    r = _ask(client, tb, "What is the secret bonus policy?")
    assert r.status_code == 200
    text = r.json()["reply"].lower()
    assert "20 percent" not in text
    assert "secret retention" not in text


def test_follow_up_uses_conversation_memory(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, user.id, "sam@example.com")
    _leave(db, org.id, emp.id, "Casual", remaining=8)
    _leave(db, org.id, emp.id, "Annual", remaining=12, days_per_year=20)
    first = _ask(client, token, "What is my leave balance?")
    assert first.status_code == 200
    cid = first.json()["conversation_id"]
    second = _ask(client, token, "How many are casual?", conversation_id=cid)
    assert second.status_code == 200
    assert "8" in second.json()["reply"]
    assert second.json()["conversation_id"] == cid


def test_grounded_refusal_when_no_payslip(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    _emp(db, org.id, user.id, "sam@example.com")
    r = _ask(client, token, "Show my payslip")
    assert r.status_code == 200
    text = r.json()["reply"].lower()
    assert "couldn" in text or "no payslip" in text or "not available" in text or "no payroll" in text
    assert "85000" not in r.json()["reply"]


def test_context_endpoint_from_jwt(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, user.id, "sam@example.com")
    r = client.get("/api/chat/context", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["user_type"] == "employee"
    assert data["employee_id"] == emp.id
    assert data["organization_id"] == org.id
    assert data["name"]
    assert "employee_id" not in (data.get("missing") or [])
