from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_org_staff, require_workforce
from app.models import Employee, Payslip, PayrollRun, SalaryStructure, User
from app.modules.workforce import employee_for_user

router = APIRouter(prefix="/api/payroll", tags=["payroll"])


class StructureIn(BaseModel):
    employee_id: str
    basic: float
    hra: float = 0
    allowance: float = 0
    tax_percent: float = 0
    other_deductions: float = 0


class RunIn(BaseModel):
    period: str
    bonus: float = 0


def _struct_ser(s: SalaryStructure, emp: Employee | None = None) -> dict:
    out = {
        "id": s.id,
        "organization_id": s.organization_id,
        "employee_id": s.employee_id,
        "basic": s.basic,
        "hra": s.hra,
        "allowance": s.allowance,
        "tax_percent": s.tax_percent,
        "other_deductions": s.other_deductions,
    }
    if emp is not None:
        out["employee_name"] = f"{emp.first_name} {emp.last_name}"
    return out


def _run_ser(run: PayrollRun, slips: list[Payslip] | None = None) -> dict:
    out = {
        "id": run.id,
        "organization_id": run.organization_id,
        "period": run.period,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "gross": 0.0,
        "tax": 0.0,
        "deductions": 0.0,
        "net": 0.0,
        "count": 0,
    }
    if slips:
        out["gross"] = round(sum(s.gross for s in slips), 2)
        out["tax"] = round(sum(s.tax for s in slips), 2)
        out["deductions"] = round(sum(s.other_deductions for s in slips), 2)
        out["net"] = round(sum(s.net for s in slips), 2)
        out["count"] = len(slips)
    return out


def _slip_ser(s: Payslip, emp: Employee | None = None) -> dict:
    out = {
        "id": s.id,
        "run_id": s.run_id,
        "employee_id": s.employee_id,
        "period": s.period,
        "basic": s.basic,
        "hra": s.hra,
        "allowance": s.allowance,
        "bonus": s.bonus,
        "gross": s.gross,
        "tax": s.tax,
        "other_deductions": s.other_deductions,
        "net": s.net,
    }
    if emp is not None:
        out["employee_name"] = f"{emp.first_name} {emp.last_name}"
        out["department"] = emp.department
    return out


def _org_id(user: User) -> str:
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    return user.organization_id


def compute(structure: SalaryStructure, bonus: float = 0) -> dict:
    gross = round(structure.basic + structure.hra + structure.allowance + bonus, 2)
    tax = round(gross * structure.tax_percent / 100.0, 2)
    deductions = round(structure.other_deductions, 2)
    net = round(gross - tax - deductions, 2)
    return {
        "basic": structure.basic,
        "hra": structure.hra,
        "allowance": structure.allowance,
        "bonus": bonus,
        "gross": gross,
        "tax": tax,
        "other_deductions": deductions,
        "net": net,
    }


@router.get("/structures")
def list_structures(user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = _org_id(user)
    rows = db.query(SalaryStructure).filter(SalaryStructure.organization_id == org_id).all()
    emps = {e.id: e for e in db.query(Employee).filter(Employee.organization_id == org_id).all()}
    return [_struct_ser(s, emps.get(s.employee_id)) for s in rows]


@router.post("/structures")
def upsert_structure(body: StructureIn, user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = _org_id(user)
    emp = db.query(Employee).filter(Employee.id == body.employee_id).first()
    if emp is None or emp.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    if body.basic < 0 or body.tax_percent < 0:
        raise HTTPException(status_code=422, detail="Invalid amounts")
    row = (
        db.query(SalaryStructure)
        .filter(SalaryStructure.employee_id == emp.id)
        .order_by(SalaryStructure.created_at.desc())
        .first()
    )
    if row is None:
        row = SalaryStructure(organization_id=org_id, employee_id=emp.id)
        db.add(row)
    row.basic = body.basic
    row.hra = body.hra
    row.allowance = body.allowance
    row.tax_percent = body.tax_percent
    row.other_deductions = body.other_deductions
    db.commit()
    db.refresh(row)
    return _struct_ser(row, emp)


@router.get("/runs")
def list_runs(user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = _org_id(user)
    runs = db.query(PayrollRun).filter(PayrollRun.organization_id == org_id).order_by(PayrollRun.period.desc()).all()
    out = []
    for run in runs:
        slips = db.query(Payslip).filter(Payslip.run_id == run.id).all()
        out.append(_run_ser(run, slips))
    return out


@router.get("/summary")
def summary(user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = _org_id(user)
    runs = db.query(PayrollRun).filter(PayrollRun.organization_id == org_id).all()
    processed = [r for r in runs if r.status == "processed"]
    draft = [r for r in runs if r.status == "draft"]
    slips = db.query(Payslip).filter(Payslip.organization_id == org_id).all()
    return {
        "processed_runs": len(processed),
        "pending_runs": len(draft),
        "gross": round(sum(s.gross for s in slips), 2),
        "tax": round(sum(s.tax for s in slips), 2),
        "deductions": round(sum(s.other_deductions for s in slips), 2),
        "net": round(sum(s.net for s in slips), 2),
    }


@router.post("/runs")
def create_run(body: RunIn, user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = _org_id(user)
    if len(body.period) != 7 or body.period[4] != "-":
        raise HTTPException(status_code=422, detail="period must be YYYY-MM")
    run = PayrollRun(organization_id=org_id, period=body.period, status="draft")
    db.add(run)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "duplicate_period", "message": "Payroll already exists for period"})
    employees = db.query(Employee).filter(Employee.organization_id == org_id, Employee.status == "active").all()
    structures = {
        s.employee_id: s
        for s in db.query(SalaryStructure).filter(SalaryStructure.organization_id == org_id).all()
    }
    slips = []
    for emp in employees:
        st = structures.get(emp.id)
        if st is None:
            continue
        calc = compute(st, body.bonus)
        slip = Payslip(organization_id=org_id, run_id=run.id, employee_id=emp.id, period=body.period, **calc)
        db.add(slip)
        slips.append(slip)
    if not slips:
        db.rollback()
        raise HTTPException(status_code=422, detail="No salary structures to process")
    db.commit()
    db.refresh(run)
    return _run_ser(run, slips)


@router.post("/runs/{run_id}/process")
def process_run(run_id: str, user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = _org_id(user)
    run = db.query(PayrollRun).filter(PayrollRun.id == run_id).first()
    if run is None or run.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Not found")
    if run.status == "processed":
        raise HTTPException(status_code=409, detail={"code": "already_processed", "message": "Already processed"})
    run.status = "processed"
    db.commit()
    db.refresh(run)
    slips = db.query(Payslip).filter(Payslip.run_id == run.id).all()
    return _run_ser(run, slips)


@router.get("/runs/{run_id}")
def get_run(run_id: str, user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = _org_id(user)
    run = db.query(PayrollRun).filter(PayrollRun.id == run_id).first()
    if run is None or run.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Not found")
    slips = db.query(Payslip).filter(Payslip.run_id == run.id).all()
    emps = {e.id: e for e in db.query(Employee).filter(Employee.organization_id == org_id).all()}
    data = _run_ser(run, slips)
    data["payslips"] = [_slip_ser(s, emps.get(s.employee_id)) for s in slips]
    return data


@router.get("/payslips")
def my_payslips(user: User = Depends(require_workforce), db: Session = Depends(get_db)):
    if user.role in ("hr", "super_admin"):
        org_id = _org_id(user)
        slips = db.query(Payslip).filter(Payslip.organization_id == org_id).order_by(Payslip.period.desc()).all()
        emps = {e.id: e for e in db.query(Employee).filter(Employee.organization_id == org_id).all()}
        return [_slip_ser(s, emps.get(s.employee_id)) for s in slips]
    emp = employee_for_user(db, user)
    slips = db.query(Payslip).filter(Payslip.employee_id == emp.id).order_by(Payslip.period.desc()).all()
    return [_slip_ser(s, emp) for s in slips]


@router.get("/payslips/{slip_id}")
def get_payslip(slip_id: str, user: User = Depends(require_workforce), db: Session = Depends(get_db)):
    slip = db.query(Payslip).filter(Payslip.id == slip_id).first()
    if slip is None:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role in ("hr", "super_admin"):
        if slip.organization_id != user.organization_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        emp = employee_for_user(db, user)
        if slip.employee_id != emp.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    emp = db.query(Employee).filter(Employee.id == slip.employee_id).first()
    return _slip_ser(slip, emp)
