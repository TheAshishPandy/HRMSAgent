from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_org_staff
from app.models import Employee, User

router = APIRouter(prefix="/api/employees", tags=["employees"])


class EmployeeIn(BaseModel):
    first_name: str
    last_name: str
    email: str
    department: str = ""
    designation: str = ""
    status: str = "active"
    joining_date: str | None = None


def _ser(e: Employee) -> dict:
    return {
        "id": e.id,
        "organization_id": e.organization_id,
        "first_name": e.first_name,
        "last_name": e.last_name,
        "email": e.email,
        "department": e.department,
        "designation": e.designation,
        "status": e.status,
        "joining_date": e.joining_date,
        "exit_date": e.exit_date,
        "exit_reason": e.exit_reason,
        "user_id": e.user_id,
    }


@router.get("")
def list_employees(user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    q = db.query(Employee)
    if user.role != "super_admin":
        q = q.filter(Employee.organization_id == user.organization_id)
    return [_ser(e) for e in q.order_by(Employee.last_name).all()]


@router.post("")
def create_employee(body: EmployeeIn, user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    org_id = user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    e = Employee(organization_id=org_id, **body.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return _ser(e)


@router.get("/{emp_id}")
def get_employee(emp_id: str, user: User = Depends(require_org_staff), db: Session = Depends(get_db)):
    e = db.query(Employee).filter(Employee.id == emp_id).first()
    if e is None:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role != "super_admin" and e.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _ser(e)


@router.patch("/{emp_id}")
def patch_employee(
    emp_id: str,
    body: EmployeeIn,
    user: User = Depends(require_org_staff),
    db: Session = Depends(get_db),
):
    e = db.query(Employee).filter(Employee.id == emp_id).first()
    if e is None:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role != "super_admin" and e.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    for k, v in body.model_dump().items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return _ser(e)
