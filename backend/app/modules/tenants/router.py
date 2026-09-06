from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_super_admin
from app.models import Organization, User
from app.themes import DEFAULT_MODULES, THEMES, serialize_org

router = APIRouter(prefix="/api/orgs", tags=["tenants"])


class OrgIn(BaseModel):
    name: str
    slug: str
    theme_key: str = "corporate_blue"
    layout_key: str = "classic_sidebar"
    modules: list[str] | None = None
    status: str = "active"


class OrgPatch(BaseModel):
    name: str | None = None
    theme_key: str | None = None
    layout_key: str | None = None
    modules: list[str] | None = None
    status: str | None = None
    logo_url: str | None = None


@router.get("/themes")
def list_themes():
    return list(THEMES.values())


@router.get("")
def list_orgs(user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return [serialize_org(o) for o in db.query(Organization).order_by(Organization.name).all()]


@router.post("")
def create_org(body: OrgIn, user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    if db.query(Organization).filter(Organization.slug == body.slug).first():
        raise HTTPException(status_code=409, detail={"code": "duplicate_slug", "message": "Slug in use"})
    if body.theme_key not in THEMES:
        raise HTTPException(status_code=422, detail="Unknown theme")
    org = Organization(
        name=body.name,
        slug=body.slug,
        theme_key=body.theme_key,
        layout_key=body.layout_key,
        modules=body.modules or list(DEFAULT_MODULES),
        status=body.status,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return serialize_org(org)


@router.patch("/{org_id}")
def patch_org(org_id: str, body: OrgPatch, user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    if "theme_key" in data and data["theme_key"] not in THEMES:
        raise HTTPException(status_code=422, detail="Unknown theme")
    for k, v in data.items():
        setattr(org, k, v)
    db.commit()
    db.refresh(org)
    return serialize_org(org)
