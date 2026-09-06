from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Employee, User

LATE_AFTER_HOUR = 9
LATE_AFTER_MINUTE = 30


def today_iso() -> str:
    return date.today().isoformat()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def employee_for_user(db: Session, user: User) -> Employee:
    emp = db.query(Employee).filter(Employee.user_id == user.id, Employee.status == "active").first()
    if emp is None:
        raise HTTPException(status_code=400, detail="No employee profile")
    return emp


def assert_org(user: User, organization_id: str) -> None:
    if user.role == "super_admin":
        return
    if not user.organization_id or user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Forbidden")


def weekday_days(start: date, end: date) -> int:
    if end < start:
        raise HTTPException(status_code=422, detail="end_date before start_date")
    days = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return days


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date")


def attendance_status_for_check_in(when: datetime) -> str:
    local = when.astimezone(timezone.utc)
    if local.hour > LATE_AFTER_HOUR or (local.hour == LATE_AFTER_HOUR and local.minute > LATE_AFTER_MINUTE):
        return "late"
    return "present"
