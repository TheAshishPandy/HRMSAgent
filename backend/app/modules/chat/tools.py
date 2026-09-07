from sqlalchemy.orm import Session

from app.crypto import decrypt_str
from app.models import (
    Application,
    AttendanceRecord,
    Employee,
    Interview,
    Job,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Payslip,
    User,
)


def get_employee_profile(db: Session, ctx: dict) -> dict | None:
    emp_id = ctx.get("employee_id")
    if not emp_id:
        return None
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if emp is None or emp.organization_id != ctx.get("organization_id"):
        return None
    manager = None
    if emp.manager_id:
        m = db.query(Employee).filter(Employee.id == emp.manager_id).first()
        if m:
            manager = f"{m.first_name} {m.last_name}"
    return {
        "employee_id": emp.id,
        "name": f"{emp.first_name} {emp.last_name}",
        "email": emp.email,
        "department": emp.department,
        "designation": emp.designation,
        "joining_date": emp.joining_date,
        "status": emp.status,
        "manager": manager,
        "organization_name": ctx.get("organization_name"),
    }


def get_leave_balances(db: Session, ctx: dict) -> list[dict]:
    emp_id = ctx.get("employee_id")
    if not emp_id:
        return []
    rows = (
        db.query(LeaveBalance)
        .filter(LeaveBalance.employee_id == emp_id, LeaveBalance.organization_id == ctx.get("organization_id"))
        .all()
    )
    types = {t.id: t for t in db.query(LeaveType).all()}
    out = []
    for b in rows:
        lt = types.get(b.leave_type_id)
        out.append({
            "leave_type": lt.name if lt else "",
            "remaining": b.remaining,
            "year": b.year,
            "days_per_year": lt.days_per_year if lt else None,
        })
    if not out:
        rows = db.query(LeaveBalance).filter(LeaveBalance.employee_id == emp_id).all()
        for b in rows:
            lt = types.get(b.leave_type_id)
            out.append({
                "leave_type": lt.name if lt else "",
                "remaining": b.remaining,
                "year": b.year,
                "days_per_year": lt.days_per_year if lt else None,
            })
    return out


def get_leave_requests(db: Session, ctx: dict) -> list[dict]:
    emp_id = ctx.get("employee_id")
    if not emp_id:
        return []
    rows = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id == emp_id)
        .order_by(LeaveRequest.created_at.desc())
        .limit(10)
        .all()
    )
    types = {t.id: t for t in db.query(LeaveType).all()}
    return [
        {
            "leave_type": types[r.leave_type_id].name if r.leave_type_id in types else "",
            "start_date": r.start_date,
            "end_date": r.end_date,
            "days": r.days,
            "status": r.status,
            "reason": r.reason,
        }
        for r in rows
    ]


def get_attendance(db: Session, ctx: dict, month: str | None = None) -> dict:
    emp_id = ctx.get("employee_id")
    if not emp_id:
        return {"records": [], "worked_days": 0}
    q = db.query(AttendanceRecord).filter(AttendanceRecord.employee_id == emp_id)
    if month:
        q = q.filter(AttendanceRecord.work_date.startswith(month))
    rows = q.order_by(AttendanceRecord.work_date.desc()).limit(60).all()
    worked = sum(1 for r in rows if r.status in ("present", "late", "remote", "half_day"))
    return {
        "worked_days": worked,
        "records": [
            {
                "work_date": r.work_date,
                "status": r.status,
                "check_in_at": r.check_in_at.isoformat() if r.check_in_at else None,
                "check_out_at": r.check_out_at.isoformat() if r.check_out_at else None,
            }
            for r in rows[:20]
        ],
    }


def get_payslips(db: Session, ctx: dict) -> list[dict]:
    emp_id = ctx.get("employee_id")
    if not emp_id:
        return []
    rows = (
        db.query(Payslip)
        .filter(Payslip.employee_id == emp_id, Payslip.organization_id == ctx.get("organization_id"))
        .order_by(Payslip.period.desc())
        .limit(12)
        .all()
    )
    return [
        {
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
        for s in rows
    ]


def get_candidate_applications(db: Session, ctx: dict) -> list[dict]:
    cand_id = ctx.get("candidate_id")
    if not cand_id:
        return []
    rows = (
        db.query(Application)
        .filter(Application.candidate_id == cand_id)
        .order_by(Application.created_at.desc())
        .all()
    )
    out = []
    for app in rows:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        if ctx.get("organization_id") and job and job.organization_id and job.organization_id != ctx.get("organization_id"):
            continue
        ivs = db.query(Interview).filter(Interview.application_id == app.id).all()
        hr_name = None
        if job:
            hr = db.query(User).filter(User.id == job.created_by).first()
            if hr:
                hr_name = decrypt_str(hr.name_enc)
        out.append({
            "application_id": app.id,
            "job_title": job.title if job else "",
            "status": app.status,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "recruiter": hr_name,
            "interviews": [
                {
                    "start_at": i.start_at.isoformat() if i.start_at else None,
                    "status": i.status,
                    "timezone": i.timezone,
                }
                for i in ivs
            ],
        })
    return out
