from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.errors import conflict
from app.models import CalendarBlock, HrWorkingHours, Interview, Job, Application, User
from app.modules.pipeline import IllegalTransition, transition


class WeekendNotAllowed(Exception):
    code = "weekend_not_allowed"


def assert_weekday(start_at: datetime, tz_name: str) -> None:
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    local = start_at.astimezone(ZoneInfo(tz_name))
    if local.weekday() >= 5:
        raise WeekendNotAllowed()


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def default_hours() -> list[dict]:
    return [
        {"weekday": i, "start_local": "09:00", "end_local": "17:00"}
        for i in range(5)
    ]


def get_hours(db: Session, hr_user_id: str) -> list[dict]:
    rows = (
        db.query(HrWorkingHours)
        .filter(HrWorkingHours.hr_user_id == hr_user_id)
        .all()
    )
    if not rows:
        return default_hours()
    return [
        {"weekday": r.weekday, "start_local": r.start_local, "end_local": r.end_local}
        for r in sorted(rows, key=lambda x: x.weekday)
    ]


def set_hours(db: Session, hr_user_id: str, hours: list[dict]) -> list[dict]:
    db.query(HrWorkingHours).filter(HrWorkingHours.hr_user_id == hr_user_id).delete()
    for h in hours:
        wd = int(h["weekday"])
        if wd < 0 or wd > 4:
            continue
        db.add(
            HrWorkingHours(
                hr_user_id=hr_user_id,
                weekday=wd,
                start_local=h["start_local"],
                end_local=h["end_local"],
            )
        )
    db.commit()
    return get_hours(db, hr_user_id)


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return _aware(a_start) < _aware(b_end) and _aware(b_start) < _aware(a_end)


def _busy(db: Session, hr_user_id: str, candidate_id: str | None) -> list[tuple[datetime, datetime]]:
    busy = []
    interviews = db.query(Interview).filter(Interview.status != "cancelled").all()
    for iv in interviews:
        app = db.query(Application).filter(Application.id == iv.application_id).first()
        if app is None:
            continue
        job = db.query(Job).filter(Job.id == app.job_id).first()
        if job and job.created_by == hr_user_id:
            busy.append((iv.start_at, iv.end_at))
        elif candidate_id and app.candidate_id == candidate_id:
            busy.append((iv.start_at, iv.end_at))
    for b in db.query(CalendarBlock).filter(CalendarBlock.hr_user_id == hr_user_id).all():
        busy.append((b.start_at, b.end_at))
    return busy


def list_open_slots(
    db: Session,
    hr_user_id: str,
    start: datetime,
    end: datetime,
    candidate_id: str | None = None,
    minutes: int = 45,
) -> list[dict]:
    hr = db.query(User).filter(User.id == hr_user_id).first()
    tz_name = hr.timezone if hr else "UTC"
    tz = ZoneInfo(tz_name)
    hours = {h["weekday"]: h for h in get_hours(db, hr_user_id)}
    busy = _busy(db, hr_user_id, candidate_id)
    start = _aware(start)
    end = _aware(end)
    slots = []
    cursor = start.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    while cursor < end.astimezone(tz):
        wd = cursor.weekday()
        if wd in hours:
            h = hours[wd]
            sh, sm = map(int, h["start_local"].split(":"))
            eh, em = map(int, h["end_local"].split(":"))
            slot = datetime.combine(cursor.date(), time(sh, sm), tzinfo=tz)
            day_end = datetime.combine(cursor.date(), time(eh, em), tzinfo=tz)
            while slot + timedelta(minutes=minutes) <= day_end:
                s_utc = slot.astimezone(timezone.utc)
                e_utc = (slot + timedelta(minutes=minutes)).astimezone(timezone.utc)
                if s_utc >= start and e_utc <= end:
                    if not any(overlaps(s_utc, e_utc, b0, b1) for b0, b1 in busy):
                        slots.append({"start_at": s_utc.isoformat(), "end_at": e_utc.isoformat()})
                slot += timedelta(minutes=minutes)
        cursor += timedelta(days=1)
    return slots


def create_interview(
    db: Session,
    application: Application,
    start_at: datetime,
    end_at: datetime,
    tz_name: str,
    hr_user_id: str,
) -> Interview:
    start_at = _aware(start_at)
    end_at = _aware(end_at)
    try:
        assert_weekday(start_at, tz_name)
    except WeekendNotAllowed:
        raise conflict("weekend_not_allowed", "Weekend slots are not allowed")
    busy = _busy(db, hr_user_id, application.candidate_id)
    if any(overlaps(start_at, end_at, b0, b1) for b0, b1 in busy):
        raise conflict("slot_conflict", "Slot conflicts with an existing booking")
    try:
        transition(application.status, "interview", has_interview=True)
    except IllegalTransition as exc:
        raise conflict(exc.code, exc.message)
    iv = Interview(
        application_id=application.id,
        start_at=start_at,
        end_at=end_at,
        timezone=tz_name,
        source="local",
        status="proposed",
    )
    db.add(iv)
    application.status = "interview"
    db.commit()
    db.refresh(iv)
    return iv
