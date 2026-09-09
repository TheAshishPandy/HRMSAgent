from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crypto import decrypt_str
from app.db import get_db
from app.deps import get_current_user, require_hr, require_org_staff
from app.errors import conflict
from app.models import Application, Employee, Job, LeaveBalance, LeaveType, Onboarding, OnboardingTask, User
from app.modules.audit import log_action
from app.modules.mail.service import send_template

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

ONBOARDING_TEMPLATE = [
    ("Offer letter signed", "contracts"),
    ("Government ID submitted", "documents"),
    ("Bank details provided", "payroll"),
    ("IT account and laptop ready", "it"),
    ("HR induction and handbook read", "hr"),
]


class OnboardingIn(BaseModel):
    application_id: str
    department: str = ""
    designation: str = ""
    joining_date: str | None = None


class OffboardIn(BaseModel):
    exit_date: str = ""
    reason: str = ""


def _org_scope(user: User, db: Session):
    if user.role == "super_admin":
        return None
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    return user.organization_id


def _task_ser(t: OnboardingTask) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "category": t.category,
        "completed": bool(t.completed),
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


def _ser(db: Session, rec: Onboarding) -> dict:
    emp = db.query(Employee).filter(Employee.id == rec.employee_id).first()
    app = db.query(Application).filter(Application.id == rec.application_id).first()
    cand = db.query(User).filter(User.id == app.candidate_id).first() if app else None
    tasks = db.query(OnboardingTask).filter(OnboardingTask.onboarding_id == rec.id).order_by(OnboardingTask.created_at).all()
    return {
        "id": rec.id,
        "organization_id": rec.organization_id,
        "employee_id": rec.employee_id,
        "employee_name": f"{emp.first_name} {emp.last_name}".strip() if emp else "",
        "employee_email": emp.email if emp else "",
        "application_id": rec.application_id,
        "job_title": (db.query(Job).filter(Job.id == app.job_id).first().title) if app else "",
        "department": rec.department,
        "designation": rec.designation,
        "joining_date": rec.joining_date,
        "status": rec.status,
        "tasks_total": rec.tasks_total,
        "completed_tasks": rec.completed_tasks,
        "candidate_id": cand.id if cand else None,
        "tasks": [_task_ser(t) for t in tasks],
        "completed_at": rec.completed_at.isoformat() if rec.completed_at else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


@router.get("/eligible")
def eligible(user: User = Depends(require_hr), db: Session = Depends(get_db)):
    org_id = _org_scope(user, db)
    q = db.query(Application).filter(Application.status == "hired")
    if org_id:
        job_ids = [row[0] for row in db.query(Job.id).filter(Job.organization_id == org_id).all()]
        q = q.filter(Application.job_id.in_(job_ids or ["__none__"]))
    onboarded = [row[0] for row in db.query(Onboarding.application_id).all()]
    rows = q.filter(~Application.id.in_(onboarded or ["__none__"])).order_by(Application.created_at.desc()).all()
    out = []
    for a in rows:
        job = db.query(Job).filter(Job.id == a.job_id).first()
        cand = db.query(User).filter(User.id == a.candidate_id).first()
        if not cand:
            continue
        out.append({
            "application_id": a.id,
            "job_id": a.job_id,
            "job_title": job.title if job else "",
            "candidate_id": cand.id,
            "candidate_name": decrypt_str(cand.name_enc),
            "candidate_email": decrypt_str(cand.email_enc),
        })
    return out


@router.post("")
def start_onboarding(body: OnboardingIn, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    org_id = user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    app = db.query(Application).filter(Application.id == body.application_id).first()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    job = db.query(Job).filter(Job.id == app.job_id).first()
    if job is None or job.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if app.status != "hired":
        raise conflict("not_hired", "Only hired applications can be onboarded")
    existing = db.query(Onboarding).filter(Onboarding.application_id == app.id).first()
    if existing:
        raise conflict("already_onboarded", "This application is already onboarded")
    cand = db.query(User).filter(User.id == app.candidate_id).first()
    if cand is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    emp = (
        db.query(Employee)
        .filter(Employee.organization_id == org_id, Employee.email == decrypt_str(cand.email_enc))
        .first()
    )
    if emp is None:
        full_name = decrypt_str(cand.name_enc)
        parts = full_name.split(" ", 1)
        first, last = (parts[0], parts[1] if len(parts) > 1 else "")
        emp = Employee(
            organization_id=org_id,
            user_id=cand.id,
            first_name=first,
            last_name=last,
            email=decrypt_str(cand.email_enc),
            department=body.department,
            designation=body.designation,
            status="active",
            joining_date=body.joining_date,
        )
        db.add(emp)
        db.flush()
    elif not emp.user_id:
        emp.user_id = cand.id
        db.flush()
    cand.role = "employee"
    cand.organization_id = org_id
    rec = Onboarding(
        organization_id=org_id,
        employee_id=emp.id,
        application_id=app.id,
        department=body.department or emp.department,
        designation=body.designation or emp.designation,
        joining_date=body.joining_date or emp.joining_date,
        status="active",
        tasks_total=len(ONBOARDING_TEMPLATE),
    )
    db.add(rec)
    db.flush()
    for title, category in ONBOARDING_TEMPLATE:
        db.add(OnboardingTask(onboarding_id=rec.id, title=title, category=category))
    year = datetime.now(timezone.utc).year
    for lt in db.query(LeaveType).filter(LeaveType.organization_id == org_id).all():
        exists = (
            db.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_id == emp.id,
                LeaveBalance.leave_type_id == lt.id,
                LeaveBalance.year == year,
            )
            .first()
        )
        if exists is None:
            db.add(LeaveBalance(
                organization_id=org_id,
                employee_id=emp.id,
                leave_type_id=lt.id,
                year=year,
                remaining=float(lt.days_per_year),
            ))
    send_template(
        db,
        to_user_id=cand.id,
        template_key="onboarding_welcome",
        context={
            "name": decrypt_str(cand.name_enc),
            "job_title": job.title,
            "joining_date": rec.joining_date or "to be confirmed",
            "department": rec.department,
            "designation": rec.designation,
        },
        related_type="onboarding",
        related_id=rec.id,
        to_email=decrypt_str(cand.email_enc),
    )
    log_action(db, user.id, "onboarded", "application", app.id, commit=True)
    db.refresh(rec)
    return _ser(db, rec)


@router.get("")
def list_onboarding(user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = _org_scope(user, db)
    q = db.query(Onboarding)
    if org_id:
        q = q.filter(Onboarding.organization_id == org_id)
    rows = q.order_by(Onboarding.created_at.desc()).all()
    return [_ser(db, r) for r in rows]


@router.get("/me")
def my_onboarding(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.user_id == user.id).order_by(Employee.created_at.desc()).first()
    if emp is None:
        raise HTTPException(status_code=404, detail="No employee profile")
    rec = (
        db.query(Onboarding)
        .filter(Onboarding.employee_id == emp.id)
        .order_by(Onboarding.created_at.desc())
        .first()
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="No onboarding record")
    return _ser(db, rec)


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    rec = db.query(Onboarding).filter(Onboarding.id == task.onboarding_id).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="Onboarding not found")
    emp = db.query(Employee).filter(Employee.id == rec.employee_id).first()
    is_owner = emp is not None and emp.user_id == user.id
    is_staff = user.role in ("hr", "super_admin")
    if not is_owner and not is_staff:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not is_staff and rec.status == "completed":
        raise conflict("completed", "Onboarding is already complete")
    if task.completed:
        return _ser(db, rec)
    task.completed = 1
    task.completed_by = user.id
    task.completed_at = datetime.now(timezone.utc)
    rec.completed_tasks += 1
    if rec.completed_tasks >= rec.tasks_total:
        rec.status = "completed"
        rec.completed_at = datetime.now(timezone.utc)
    db.commit()
    log_action(db, user.id, "onboarding_task_done", "onboarding", rec.id, commit=True)
    db.refresh(rec)
    return _ser(db, rec)


@router.post("/employees/{emp_id}/offboard")
def offboard(emp_id: str, body: OffboardIn, user: User = Depends(require_hr), db: Session = Depends(get_db)):
    org_id = _org_scope(user, db)
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if org_id and emp.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if emp.user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot offboard yourself")
    emp.status = "inactive"
    emp.exit_date = body.exit_date or None
    emp.exit_reason = body.reason
    if emp.user_id:
        target = db.query(User).filter(User.id == emp.user_id).first()
        if target is not None:
            send_template(
                db,
                to_user_id=target.id,
                template_key="offboarding_notice",
                context={
                    "name": f"{emp.first_name} {emp.last_name}".strip(),
                    "exit_date": body.exit_date or "to be confirmed",
                    "reason": body.reason or "Not provided",
                },
                related_type="employee",
                related_id=emp.id,
                to_email=emp.email,
            )
    log_action(db, user.id, "offboarded", "employee", emp.id, commit=True)
    db.commit()
    db.refresh(emp)
    return {
        "id": emp.id,
        "status": emp.status,
        "exit_date": emp.exit_date,
        "exit_reason": emp.exit_reason,
    }
