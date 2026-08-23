from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.db.models import AuditLog, ClinicalCase, User
from app.dependencies import DbSession, require_permission
from app.schemas import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    db: DbSession,
    user: User = Depends(require_permission("audit:read")),
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLog]:
    statement = (
        select(AuditLog)
        .where(AuditLog.organization_id == user.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if entity_type:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if entity_id:
        statement = statement.where(AuditLog.entity_id == entity_id)
    return list(db.scalars(statement).all())


@router.get("/cases/{case_id}", response_model=list[AuditLogRead])
def list_case_audit_logs(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("audit:case_read")),
) -> list[AuditLog]:
    case = db.get(ClinicalCase, case_id)
    if not case or case.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.organization_id == user.organization_id,
                AuditLog.entity_type == "case",
                AuditLog.entity_id == case_id,
            )
            .order_by(AuditLog.created_at.asc())
        ).all()
    )
