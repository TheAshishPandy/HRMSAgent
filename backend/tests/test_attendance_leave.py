from datetime import date, timedelta

from app.models import Employee, LeaveBalance, LeaveType
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


def test_check_in_out_and_duplicate(client, db):
    org = _org(db, "Org A", "org-a")
    user, token = _user(db, "sam@example.com", "employee", org.id)
    _emp(db, org.id, user.id, "sam@example.com")
    r = client.post("/api/attendance/check-in", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["status"] in ("present", "late")
    again = client.post("/api/attendance/check-in", headers=_auth(token))
    assert again.status_code == 409
    out = client.post("/api/attendance/check-out", headers=_auth(token))
    assert out.status_code == 200
    assert out.json()["check_out_at"]


def test_hr_today_board_is_org_scoped(client, db):
    a = _org(db, "Org A", "org-a")
    b = _org(db, "Org B", "org-b")
    ha_user, ha = _user(db, "hra@example.com", "hr", a.id)
    _emp(db, a.id, ha_user.id, "hra@example.com", "Pat", "HR")
    sb, st = _user(db, "sam@example.com", "employee", a.id)
    _emp(db, a.id, sb.id, "sam@example.com")
    ub, tb = _user(db, "bob@example.com", "employee", b.id)
    _emp(db, b.id, ub.id, "bob@example.com", "Bob", "B")
    client.post("/api/attendance/check-in", headers=_auth(st))
    board = client.get("/api/attendance/today", headers=_auth(ha))
    assert board.status_code == 200
    names = [row["employee_name"] for row in board.json()["rows"]]
    assert "Sam Lee" in names
    assert "Bob B" not in names


def test_leave_apply_approve_and_balance(client, db):
    org = _org(db, "Org A", "org-a")
    hr_user, hr = _user(db, "hr@example.com", "hr", org.id)
    _emp(db, org.id, hr_user.id, "hr@example.com", "Pat", "HR")
    emp_user, et = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, emp_user.id, "sam@example.com")
    lt = LeaveType(organization_id=org.id, name="Annual", days_per_year=10, paid=1)
    db.add(lt)
    db.commit()
    db.refresh(lt)
    start = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    end = start
    applied = client.post("/api/leave/requests", json={
        "leave_type_id": lt.id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "reason": "off",
    }, headers=_auth(et))
    assert applied.status_code == 200
    req_id = applied.json()["id"]
    overlap = client.post("/api/leave/requests", json={
        "leave_type_id": lt.id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "reason": "again",
    }, headers=_auth(et))
    assert overlap.status_code == 409
    decided = client.post(
        f"/api/leave/requests/{req_id}/decide",
        json={"status": "approved"},
        headers=_auth(hr),
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    bals = client.get("/api/leave/balances", headers=_auth(et)).json()
    annual = next(b for b in bals if b["leave_type_id"] == lt.id)
    assert annual["remaining"] == 9


def test_leave_insufficient_balance(client, db):
    org = _org(db, "Org A", "org-a")
    emp_user, et = _user(db, "sam@example.com", "employee", org.id)
    emp = _emp(db, org.id, emp_user.id, "sam@example.com")
    lt = LeaveType(organization_id=org.id, name="Casual", days_per_year=1, paid=1)
    db.add(lt)
    db.flush()
    db.add(LeaveBalance(
        organization_id=org.id,
        employee_id=emp.id,
        leave_type_id=lt.id,
        year=date.today().year,
        remaining=0,
    ))
    db.commit()
    start = date.today()
    while start.weekday() >= 5:
        start += timedelta(days=1)
    r = client.post("/api/leave/requests", json={
        "leave_type_id": lt.id,
        "start_date": start.isoformat(),
        "end_date": start.isoformat(),
        "reason": "x",
    }, headers=_auth(et))
    assert r.status_code == 409
