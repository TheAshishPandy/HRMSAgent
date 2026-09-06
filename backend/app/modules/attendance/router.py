from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_org_staff, require_workforce
from app.models import AttendanceRecord, Employee, LeaveRequest, User
from app.modules.workforce import attendance_status_for_check_in, employee_for_user, now_utc, today_iso

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def _ser(row: AttendanceRecord, employee: Employee | None = None) -> dict:
    out = {
        "id": row.id,
        "organization_id": row.organization_id,
        "employee_id": row.employee_id,
        "work_date": row.work_date,
        "check_in_at": row.check_in_at.isoformat() if row.check_in_at else None,
        "check_out_at": row.check_out_at.isoformat() if row.check_out_at else None,
        "status": row.status,
        "notes": row.notes,
    }
    if employee is not None:
        out["employee_name"] = f"{employee.first_name} {employee.last_name}"
        out["department"] = employee.department
    return out


@router.get("/today")
def today_board(
    work_date: str | None = Query(default=None),
    user: User = Depends(require_org_staff),
    db: Session = Depends(get_db),
):
    org_id = user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    day = work_date or today_iso()
    employees = (
        db.query(Employee)
        .filter(Employee.organization_id == org_id, Employee.status == "active")
        .order_by(Employee.last_name)
        .all()
    )
    records = {
        r.employee_id: r
        for r in db.query(AttendanceRecord).filter(
            AttendanceRecord.organization_id == org_id,
            AttendanceRecord.work_date == day,
        ).all()
    }
    on_leave_ids = {
        r.employee_id
        for r in db.query(LeaveRequest).filter(
            LeaveRequest.organization_id == org_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= day,
            LeaveRequest.end_date >= day,
        ).all()
    }
    rows = []
    counts = {"present": 0, "late": 0, "absent": 0, "on_leave": 0, "remote": 0, "half_day": 0}
    for emp in employees:
        rec = records.get(emp.id)
        if rec is None and emp.id in on_leave_ids:
            status = "on_leave"
            payload = {
                "id": None,
                "organization_id": org_id,
                "employee_id": emp.id,
                "work_date": day,
                "check_in_at": None,
                "check_out_at": None,
                "status": status,
                "notes": None,
                "employee_name": f"{emp.first_name} {emp.last_name}",
                "department": emp.department,
            }
        elif rec is None:
            status = "absent"
            payload = {
                "id": None,
                "organization_id": org_id,
                "employee_id": emp.id,
                "work_date": day,
                "check_in_at": None,
                "check_out_at": None,
                "status": status,
                "notes": None,
                "employee_name": f"{emp.first_name} {emp.last_name}",
                "department": emp.department,
            }
        else:
            payload = _ser(rec, emp)
            status = rec.status
        counts[status] = counts.get(status, 0) + 1
        rows.append(payload)
    return {"work_date": day, "counts": counts, "rows": rows}


@router.get("/me")
def my_attendance(
    user: User = Depends(require_workforce),
    db: Session = Depends(get_db),
):
    emp = employee_for_user(db, user)
    rows = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.employee_id == emp.id)
        .order_by(AttendanceRecord.work_date.desc())
        .limit(60)
        .all()
    )
    return [_ser(r, emp) for r in rows]


@router.post("/check-in")
def check_in(user: User = Depends(require_workforce), db: Session = Depends(get_db)):
    emp = employee_for_user(db, user)
    day = today_iso()
    existing = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.employee_id == emp.id, AttendanceRecord.work_date == day)
        .first()
    )
    if existing and existing.check_in_at:
        raise HTTPException(status_code=409, detail={"code": "already_checked_in", "message": "Already checked in"})
    when = now_utc()
    if existing is None:
        existing = AttendanceRecord(
            organization_id=emp.organization_id,
            employee_id=emp.id,
            work_date=day,
        )
        db.add(existing)
    existing.check_in_at = when
    existing.status = attendance_status_for_check_in(when)
    db.commit()
    db.refresh(existing)
    return _ser(existing, emp)


@router.post("/check-out")
def check_out(user: User = Depends(require_workforce), db: Session = Depends(get_db)):
    emp = employee_for_user(db, user)
    day = today_iso()
    existing = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.employee_id == emp.id, AttendanceRecord.work_date == day)
        .first()
    )
    if existing is None or not existing.check_in_at:
        raise HTTPException(status_code=409, detail={"code": "not_checked_in", "message": "Check in first"})
    if existing.check_out_at:
        raise HTTPException(status_code=409, detail={"code": "already_checked_out", "message": "Already checked out"})
    existing.check_out_at = now_utc()
    db.commit()
    db.refresh(existing)
    return _ser(existing, emp)


class CorrectionIn(BaseModel):
    employee_id: str
    work_date: str
    status: str
    notes: str | None = None


@router.post("/correct")
def correct(
    body: CorrectionIn,
    user: User = Depends(require_org_staff),
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).filter(Employee.id == body.employee_id).first()
    if emp is None:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role != "super_admin" and emp.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if body.status not in ("present", "late", "absent", "on_leave", "remote", "half_day"):
        raise HTTPException(status_code=422, detail="Unknown status")
    rec = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.employee_id == emp.id, AttendanceRecord.work_date == body.work_date)
        .first()
    )
    if rec is None:
        rec = AttendanceRecord(
            organization_id=emp.organization_id,
            employee_id=emp.id,
            work_date=body.work_date,
        )
        db.add(rec)
    rec.status = body.status
    rec.notes = body.notes
    db.commit()
    db.refresh(rec)
    return _ser(rec, emp)
