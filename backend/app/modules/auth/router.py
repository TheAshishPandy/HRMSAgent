from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.modules.auth import schemas
from app.modules.auth.service import authenticate, create_token, register, user_public

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register_user(body: schemas.RegisterIn, db: Session = Depends(get_db)):
    user = register(db, body.email, body.password, body.name, body.role)
    return {"token": create_token(user.id, user.role), "user": user_public(user, db)}


@router.post("/login")
def login_user(body: schemas.LoginIn, db: Session = Depends(get_db)):
    user = authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(user.id, user.role), "user": user_public(user, db)}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.config import get_settings

    s = get_settings()
    data = user_public(user, db)
    data["timezone"] = user.timezone
    data["integrations"] = {
        "smtp_configured": bool(s.smtp_host),
        "google_configured": bool(s.google_client_id and s.google_client_secret),
        "llm_configured": bool(s.user_llm_api_key),
        "google_connected": bool(user.google_refresh_token_enc),
    }
    return data
