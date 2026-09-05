from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(
    db: Session,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    *,
    commit: bool = False,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    )
    if commit:
        db.commit()
