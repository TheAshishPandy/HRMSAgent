from app.models import Employee, SalaryStructure
from tests.test_tenants import _auth, _org, _user


def _emp(db, org_id, user_id, email, first="Sam", last="Lee"):
    e = Employee(
        organization_id=org_id,
        user_id=user_id,
        first_name=first,
        last_name=last,
        email=email,
        department="Eng",
        designation="IC",
        status="active",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_payroll_run_and_process(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hr = _user(db, "hr@example.com", "hr", org.id)
    emp_user, et = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, emp_user.id, "sam@example.com")
    st = client.post("/api/payroll/structures", json={
        "employee_id": emp.id,
        "basic": 100000,
        "hra": 20000,
        "allowance": 5000,
        "tax_percent": 10,
        "other_deductions": 1000,
    }, headers=_auth(hr))
    assert st.status_code == 200
    run = client.post("/api/payroll/runs", json={"period": "2026-09"}, headers=_auth(hr))
    assert run.status_code == 200
    assert run.json()["gross"] == 125000
    assert run.json()["tax"] == 12500
    assert run.json()["net"] == 111500
    processed = client.post(f"/api/payroll/runs/{run.json()['id']}/process", headers=_auth(hr))
    assert processed.status_code == 200
    assert processed.json()["status"] == "processed"
    again = client.post("/api/payroll/runs", json={"period": "2026-09"}, headers=_auth(hr))
    assert again.status_code == 409
    slips = client.get("/api/payroll/payslips", headers=_auth(et))
    assert slips.status_code == 200
    assert len(slips.json()) == 1
    assert slips.json()[0]["net"] == 111500


def test_payroll_tenant_isolation(client, db):
    a = _org(db, "Org A", "org-a")
    b = _org(db, "Org B", "org-b")
    _, ha = _user(db, "hra@example.com", "hr", a.id)
    _, hb = _user(db, "hrb@example.com", "hr", b.id)
    ua, ta = _user(db, "sam@example.com", "employee", a.id)
    emp_a = _emp(db, a.id, ua.id, "sam@example.com")
    ub, tb = _user(db, "bob@example.com", "employee", b.id)
    emp_b = _emp(db, b.id, ub.id, "bob@example.com", "Bob", "B")
    client.post("/api/payroll/structures", json={
        "employee_id": emp_a.id, "basic": 50000, "tax_percent": 0,
    }, headers=_auth(ha))
    client.post("/api/payroll/structures", json={
        "employee_id": emp_b.id, "basic": 80000, "tax_percent": 0,
    }, headers=_auth(hb))
    client.post("/api/payroll/runs", json={"period": "2026-08"}, headers=_auth(ha))
    slips_b = client.get("/api/payroll/payslips", headers=_auth(tb)).json()
    assert slips_b == []
    runs_b = client.get("/api/payroll/runs", headers=_auth(hb)).json()
    assert runs_b == []


def test_employee_cannot_create_run(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    _emp(db, org.id, user.id, "sam@example.com")
    r = client.post("/api/payroll/runs", json={"period": "2026-09"}, headers=_auth(token))
    assert r.status_code == 403
