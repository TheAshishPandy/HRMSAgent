import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            creds.credentials,
            get_settings().jwt_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = (
        db.query(User)
        .filter(User.id == user_id, User.deleted_at.is_(None))
        .first()
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def require_hr(user: User = Depends(get_current_user)) -> User:
    if user.role != "hr":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user
