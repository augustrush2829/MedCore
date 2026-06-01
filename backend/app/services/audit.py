import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog, User


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def write_audit(
    db: Session,
    *,
    user: User,
    action: str,
    entity_type: str,
    entity_id: str,
    before: Any | None = None,
    after: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    event = AuditLog(
        organization_id=user.organization_id,
        actor_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_hash=stable_hash(before) if before is not None else None,
        after_hash=stable_hash(after) if after is not None else None,
        metadata_json=metadata or {},
    )
    db.add(event)
    return event

