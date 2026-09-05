from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_hr
from app.models import User
from app.modules.jobs import schemas, service
from app.modules.jobs.service import serialize_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
_bearer = HTTPBearer(auto_error=False)


def _optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if creds is None or not creds.credentials:
        return None
    return get_current_user(creds, db)


def _is_hr(user: User | None) -> bool:
    return user is not None and user.role == "hr"


@router.post("")
def create_job(
    body: schemas.JobCreate,
    user: User = Depends(require_hr),
    db: Session = Depends(get_db),
):
    job = service.create_job(db, user.id, body.model_dump())
    return serialize_job(job, hr=True)


@router.get("")
def list_jobs(
    user: User | None = Depends(_optional_user),
    db: Session = Depends(get_db),
):
    hr = _is_hr(user)
    jobs = service.list_jobs(db, hr=hr)
    return [serialize_job(j, hr=hr) for j in jobs]


@router.get("/{job_id}")
def get_one(
    job_id: str,
    user: User | None = Depends(_optional_user),
    db: Session = Depends(get_db),
):
    job = service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    hr = _is_hr(user)
    if not hr and job.status != "open":
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_job(job, hr=hr)


@router.patch("/{job_id}")
def patch_job(
    job_id: str,
    body: schemas.JobUpdate,
    user: User = Depends(require_hr),
    db: Session = Depends(get_db),
):
    job = service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = service.update_job(db, job, body.model_dump(exclude_unset=True))
    return serialize_job(job, hr=True)


@router.post("/{job_id}/publish")
def publish_job(
    job_id: str,
    user: User = Depends(require_hr),
    db: Session = Depends(get_db),
):
    job = service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = service.set_status(db, job, "open")
    return serialize_job(job, hr=True)


@router.post("/{job_id}/close")
def close_job(
    job_id: str,
    user: User = Depends(require_hr),
    db: Session = Depends(get_db),
):
    job = service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = service.set_status(db, job, "closed")
    return serialize_job(job, hr=True)


@router.get("/{job_id}/export.md")
def export_md(
    job_id: str,
    user: User = Depends(require_hr),
    db: Session = Depends(get_db),
):
    job = service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return Response(content=job.jd_markdown, media_type="text/markdown")


@router.get("/{job_id}/export.pdf")
def export_pdf(
    job_id: str,
    user: User = Depends(require_hr),
    db: Session = Depends(get_db),
):
    job = service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 48
    for line in job.jd_markdown.splitlines():
        if y < 48:
            c.showPage()
            y = height - 48
        c.drawString(48, y, line[:110])
        y -= 14
    c.save()
    return Response(content=buf.getvalue(), media_type="application/pdf")
