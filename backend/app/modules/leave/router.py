from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_org_staff, require_workforce
from app.models import Employee, LeaveBalance, LeaveRequest, LeaveType, User
from app.modules.workforce import employee_for_user, parse_iso_date, weekday_days

router = APIRouter(prefix="/api/leave", tags=["leave"])


def _type_ser(t: LeaveType) -> dict:
    return {
        "id": t.id,
        "organization_id": t.organization_id,
        "name": t.name,
        "days_per_year": t.days_per_year,
        "paid": bool(t.paid),
    }


def _req_ser(r: LeaveRequest, emp: Employee | None = None, lt: LeaveType | None = None) -> dict:
    out = {
        "id": r.id,
        "organization_id": r.organization_id,
        "employee_id": r.employee_id,
        "leave_type_id": r.leave_type_id,
        "start_date": r.start_date,
        "end_date": r.end_date,
        "days": r.days,
        "reason": r.reason,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
    if emp is not None:
        out["employee_name"] = f"{emp.first_name} {emp.last_name}"
    if lt is not None:
        out["leave_type_name"] = lt.name
    return out


class LeaveTypeIn(BaseModel):
    name: str
    days_per_year: int
    paid: bool = True


class LeaveApplyIn(BaseModel):
    leave_type_id: str
    start_date: str
    end_date: str
    reason: str = ""


class DecideIn(BaseModel):
    status: str


def _ensure_balance(db: Session, emp: Employee, lt: LeaveType, year: int) -> LeaveBalance:
    bal = (
        db.query(LeaveBalance)
        .filter(
            LeaveBalance.employee_id == emp.id,
            LeaveBalance.leave_type_id == lt.id,
            LeaveBalance.year == year,
        )
        .first()
    )
    if bal is None:
        bal = LeaveBalance(
            organization_id=emp.organization_id,
            employee_id=emp.id,
            leave_type_id=lt.id,
            year=year,
            remaining=float(lt.days_per_year),
        )
        db.add(bal)
        db.flush()
    return bal


@router.get("/types")
def list_types(user: User = Depends(require_workforce), db: Session = Depends(get_db)):
    org_id = user.organization_id
    if user.role == "employee":
        emp = employee_for_user(db, user)
        org_id = emp.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    return [_type_ser(t) for t in db.query(LeaveType).filter(LeaveType.organization_id == org_id).all()]


@router.post("/types")
def create_type(body: LeaveTypeIn, user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    t = LeaveType(
        organization_id=user.organization_id,
        name=body.name,
        days_per_year=body.days_per_year,
        paid=1 if body.paid else 0,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _type_ser(t)


@router.get("/balances")
def balances(user: User = Depends(require_workforce), db: Session = Depends(get_db)):
    if user.role in ("hr", "super_admin"):
        org_id = user.organization_id
        if not org_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        rows = db.query(LeaveBalance).filter(LeaveBalance.organization_id == org_id).all()
    else:
        emp = employee_for_user(db, user)
        rows = db.query(LeaveBalance).filter(LeaveBalance.employee_id == emp.id).all()
    types = {t.id: t for t in db.query(LeaveType).all()}
    emps = {e.id: e for e in db.query(Employee).all()}
    out = []
    for b in rows:
        item = {
            "id": b.id,
            "employee_id": b.employee_id,
            "leave_type_id": b.leave_type_id,
            "year": b.year,
            "remaining": b.remaining,
            "leave_type_name": types[b.leave_type_id].name if b.leave_type_id in types else "",
        }
        emp = emps.get(b.employee_id)
        if emp:
            item["employee_name"] = f"{emp.first_name} {emp.last_name}"
        out.append(item)
    return out


@router.get("/requests")
def list_requests(user: User = Depends(require_workforce), db: Session = Depends(get_db)):
    q = db.query(LeaveRequest)
    if user.role in ("hr", "super_admin"):
        if user.organization_id:
            q = q.filter(LeaveRequest.organization_id == user.organization_id)
    else:
        emp = employee_for_user(db, user)
        q = q.filter(LeaveRequest.employee_id == emp.id)
    rows = q.order_by(LeaveRequest.created_at.desc()).all()
    types = {t.id: t for t in db.query(LeaveType).all()}
    emps = {e.id: e for e in db.query(Employee).all()}
    return [_req_ser(r, emps.get(r.employee_id), types.get(r.leave_type_id)) for r in rows]


@router.post("/requests")
def apply(body: LeaveApplyIn, user: User = Depends(require_workforce), db: Session = Depends(get_db)):
    emp = employee_for_user(db, user) if user.role == "employee" else None
    if emp is None and user.role in ("hr", "super_admin"):
        emp = employee_for_user(db, user)
    start = parse_iso_date(body.start_date)
    end = parse_iso_date(body.end_date)
    days = weekday_days(start, end)
    if days <= 0:
        raise HTTPException(status_code=422, detail="No weekday days in range")
    lt = db.query(LeaveType).filter(LeaveType.id == body.leave_type_id).first()
    if lt is None or lt.organization_id != emp.organization_id:
        raise HTTPException(status_code=404, detail="Leave type not found")
    overlap = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.status.in_(["pending", "approved"]),
            LeaveRequest.start_date <= body.end_date,
            LeaveRequest.end_date >= body.start_date,
        )
        .first()
    )
    if overlap:
        raise HTTPException(status_code=409, detail={"code": "overlap", "message": "Overlapping leave request"})
    bal = _ensure_balance(db, emp, lt, start.year)
    if bal.remaining < days:
        raise HTTPException(status_code=409, detail={"code": "insufficient_balance", "message": "Not enough leave days"})
    req = LeaveRequest(
        organization_id=emp.organization_id,
        employee_id=emp.id,
        leave_type_id=lt.id,
        start_date=body.start_date,
        end_date=body.end_date,
        days=float(days),
        reason=body.reason,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _req_ser(req, emp, lt)


@router.post("/requests/{req_id}/decide")
def decide(
    req_id: str,
    body: DecideIn,
    user: User = Depends(require_org_staff),
    db: Session = Depends(get_db),
):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=422, detail="status must be approved or rejected")
    req = db.query(LeaveRequest).filter(LeaveRequest.id == req_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role != "super_admin" and req.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail={"code": "already_decided", "message": "Already decided"})
    emp = db.query(Employee).filter(Employee.id == req.employee_id).first()
    lt = db.query(LeaveType).filter(LeaveType.id == req.leave_type_id).first()
    if body.status == "approved":
        start = parse_iso_date(req.start_date)
        bal = _ensure_balance(db, emp, lt, start.year)
        if bal.remaining < req.days:
            raise HTTPException(status_code=409, detail={"code": "insufficient_balance", "message": "Not enough leave days"})
        bal.remaining -= req.days
    req.status = body.status
    req.decided_by = user.id
    db.commit()
    db.refresh(req)
    return _req_ser(req, emp, lt)
