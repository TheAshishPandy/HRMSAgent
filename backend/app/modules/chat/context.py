from sqlalchemy.orm import Session

from app.crypto import decrypt_str
from app.models import Employee, Organization, User


def resolve_user_context(db: Session, user: User) -> dict:
    name = decrypt_str(user.name_enc)
    email = decrypt_str(user.email_enc)
    emp = (
        db.query(Employee)
        .filter(Employee.user_id == user.id, Employee.status == "active")
        .first()
    )
    org = None
    if user.organization_id:
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if emp is None and org is None and user.role == "candidate":
        pass
    user_type = "candidate"
    if user.role in ("employee", "hr", "super_admin") and emp is not None:
        user_type = "employee"
    elif user.role in ("hr", "super_admin") and emp is None:
        user_type = "staff"
    elif user.role == "candidate":
        user_type = "candidate"
    ctx = {
        "user_id": user.id,
        "user_type": user_type,
        "role": user.role,
        "name": emp.first_name + " " + emp.last_name if emp else name,
        "email": email,
        "organization_id": user.organization_id or (emp.organization_id if emp else None),
        "organization_name": org.name if org else None,
        "employee_id": emp.id if emp else None,
        "candidate_id": user.id if user.role == "candidate" else None,
        "department": emp.department if emp else None,
        "designation": emp.designation if emp else None,
        "joining_date": emp.joining_date if emp else None,
        "manager_id": emp.manager_id if emp else None,
    }
    return ctx
