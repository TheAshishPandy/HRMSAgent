from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import decrypt_str, encrypt_str, hmac_email
from app.models import Organization, User
from app.themes import serialize_org

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")


def user_public(user: User, db: Session | None = None) -> dict:
    data = {
        "id": user.id,
        "email": decrypt_str(user.email_enc),
        "name": decrypt_str(user.name_enc),
        "role": user.role,
        "organization_id": user.organization_id,
        "organization": None,
    }
    if db is not None and user.organization_id:
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if org is not None:
            data["organization"] = serialize_org(org)
    return data


def _hr_exists(db: Session) -> bool:
    return (
        db.query(User)
        .filter(User.role == "hr", User.deleted_at.is_(None))
        .first()
        is not None
    )


def register(db: Session, email: str, password: str, name: str, role: str) -> User:
    if role not in ("hr", "candidate"):
        role = "candidate"
    if role == "hr" and _hr_exists(db):
        role = "candidate"
    user = User(
        email_enc=encrypt_str(email),
        email_hash=hmac_email(email),
        password_hash=hash_password(password),
        role=role,
        name_enc=encrypt_str(name),
        timezone="UTC",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail={"code": "duplicate_email", "message": "Email already registered"})
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = (
        db.query(User)
        .filter(User.email_hash == hmac_email(email), User.deleted_at.is_(None))
        .first()
    )
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
