from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.db.models import AIResponse, AuditLog, ClinicalCase, Organization, Patient, PatientPortalAccount, PatientPortalExplanation, User
from app.dependencies import DbSession, require_permission
from app.routers.auth import to_user_read
from app.routers.patient_portal import to_explanation_read
from app.schemas import (
    AdminOverview,
    AdminPortalExplanationRead,
    AdminPortalExplanationUpdate,
    AdminUserCreate,
    AdminUserUpdate,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
    OrganizationUserCreate,
    UserRead,
)
from app.services.audit import write_audit
from app.services.image_storage import object_exists, presigned_download_url

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/organizations", response_model=list[OrganizationRead])
def list_organizations(
    db: DbSession,
    user: User = Depends(require_permission("super_admin:organizations")),
) -> list[Organization]:
    return list(db.scalars(select(Organization).order_by(Organization.created_at.desc())).all())


@router.post("/organizations", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    db: DbSession,
    user: User = Depends(require_permission("super_admin:organizations")),
) -> Organization:
    existing_admin = db.scalar(select(User).where(User.email == payload.admin_email))
    if existing_admin:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin email already exists")
    organization = Organization(
        name=payload.name,
        plan=payload.plan,
        status=payload.status,
        settings=payload.settings,
    )
    db.add(organization)
    db.flush()
    hospital_admin = User(
        organization_id=organization.id,
        email=payload.admin_email,
        name=payload.admin_name,
        role="admin",
        password_hash=hash_password(payload.admin_password),
    )
    db.add(hospital_admin)
    db.flush()
    write_audit(
        db,
        user=user,
        action="super_admin.organization.create",
        entity_type="organization",
        entity_id=organization.id,
        after={"name": organization.name, "admin_email": hospital_admin.email},
    )
    db.commit()
    db.refresh(organization)
    return organization


@router.patch("/organizations/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    db: DbSession,
    user: User = Depends(require_permission("super_admin:organizations")),
) -> Organization:
    organization = db.get(Organization, organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    before = {"name": organization.name, "plan": organization.plan, "status": organization.status, "settings": organization.settings}
    if payload.name is not None:
        organization.name = payload.name
    if payload.plan is not None:
        organization.plan = payload.plan
    if payload.status is not None:
        organization.status = payload.status
    if payload.settings is not None:
        organization.settings = payload.settings
    after = {"name": organization.name, "plan": organization.plan, "status": organization.status, "settings": organization.settings}
    write_audit(db, user=user, action="super_admin.organization.update", entity_type="organization", entity_id=organization.id, before=before, after=after)
    db.commit()
    db.refresh(organization)
    return organization


@router.post("/organizations/{organization_id}/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_organization_user(
    organization_id: str,
    payload: OrganizationUserCreate,
    db: DbSession,
    user: User = Depends(require_permission("super_admin:organizations")),
) -> UserRead:
    organization = db.get(Organization, organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    existing = db.scalar(select(User).where(User.organization_id == organization.id, User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User email already exists in organization")
    created = User(
        organization_id=organization.id,
        email=payload.email,
        name=payload.name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(created)
    db.flush()
    write_audit(
        db,
        user=user,
        action="super_admin.organization_user.create",
        entity_type="user",
        entity_id=created.id,
        after={"organization_id": organization.id, "email": created.email, "role": created.role},
    )
    db.commit()
    db.refresh(created)
    return to_user_read(created)


@router.get("/overview", response_model=AdminOverview)
def admin_overview(
    db: DbSession,
    user: User = Depends(require_permission("admin:overview")),
) -> AdminOverview:
    organization_id = user.organization_id
    users_total = count_model(db, User, User.organization_id == organization_id)
    active_users = count_model(db, User, User.organization_id == organization_id, User.status == "active")
    patients_total = count_model(db, Patient, Patient.organization_id == organization_id)
    cases_total = count_model(db, ClinicalCase, ClinicalCase.organization_id == organization_id)
    ai_responses_total = count_model(db, AIResponse, AIResponse.organization_id == organization_id)
    portal_accounts_total = count_model(db, PatientPortalAccount, PatientPortalAccount.organization_id == organization_id)
    portal_uploads_total = count_model(db, PatientPortalExplanation, PatientPortalExplanation.organization_id == organization_id)
    portal_uploads_requiring_review = count_model(
        db,
        PatientPortalExplanation,
        PatientPortalExplanation.organization_id == organization_id,
        PatientPortalExplanation.extraction_status == "requires_review",
    )
    audit_events_total = count_model(db, AuditLog, AuditLog.organization_id == organization_id)
    return AdminOverview(
        organization_id=organization_id,
        users_total=users_total,
        active_users=active_users,
        patients_total=patients_total,
        cases_total=cases_total,
        ai_responses_total=ai_responses_total,
        portal_accounts_total=portal_accounts_total,
        portal_uploads_total=portal_uploads_total,
        portal_uploads_requiring_review=portal_uploads_requiring_review,
        audit_events_total=audit_events_total,
    )


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: DbSession,
    user: User = Depends(require_permission("user:manage")),
) -> list[UserRead]:
    users = db.scalars(
        select(User)
        .where(User.organization_id == user.organization_id)
        .order_by(User.created_at.desc())
    ).all()
    return [to_user_read(item) for item in users]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    db: DbSession,
    user: User = Depends(require_permission("user:manage")),
) -> UserRead:
    if payload.role == "admin" and user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admin can create hospital admins")
    existing = db.scalar(select(User).where(User.organization_id == user.organization_id, User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User email already exists")
    created = User(
        organization_id=user.organization_id,
        email=payload.email,
        name=payload.name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(created)
    db.flush()
    write_audit(db, user=user, action="admin.user.create", entity_type="user", entity_id=created.id, after={"email": created.email, "role": created.role})
    db.commit()
    db.refresh(created)
    return to_user_read(created)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    db: DbSession,
    user: User = Depends(require_permission("user:manage")),
) -> UserRead:
    target = db.get(User, user_id)
    if not target or target.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    before = {"name": target.name, "role": target.role, "status": target.status}
    if payload.name is not None:
        target.name = payload.name
    if payload.role is not None:
        target.role = payload.role
    if payload.status is not None:
        target.status = payload.status
    target.updated_at = datetime.now(timezone.utc)
    after = {"name": target.name, "role": target.role, "status": target.status}
    write_audit(db, user=user, action="admin.user.update", entity_type="user", entity_id=target.id, before=before, after=after)
    db.commit()
    db.refresh(target)
    return to_user_read(target)


@router.get("/portal-explanations", response_model=list[AdminPortalExplanationRead])
def list_portal_explanations(
    db: DbSession,
    user: User = Depends(require_permission("admin:portal_uploads")),
    status_filter: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AdminPortalExplanationRead]:
    statement = (
        select(PatientPortalExplanation)
        .options(selectinload(PatientPortalExplanation.patient))
        .where(PatientPortalExplanation.organization_id == user.organization_id)
        .order_by(PatientPortalExplanation.created_at.desc())
        .limit(limit)
    )
    if status_filter:
        statement = statement.where(PatientPortalExplanation.extraction_status == status_filter)
    explanations = db.scalars(statement).all()
    return [to_admin_portal_explanation(item) for item in explanations]


@router.get("/portal-explanations/{explanation_id}/image")
def get_portal_explanation_image(
    explanation_id: str,
    db: DbSession,
    user: User = Depends(require_permission("admin:portal_uploads")),
) -> RedirectResponse:
    explanation = db.get(PatientPortalExplanation, explanation_id)
    if (
        not explanation
        or explanation.organization_id != user.organization_id
        or not explanation.attachment_object_key
        or not object_exists(explanation.attachment_object_key)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    write_audit(db, user=user, action="admin.portal_image.view", entity_type="patient_portal_explanation", entity_id=explanation.id)
    db.commit()
    url = presigned_download_url(
        explanation.attachment_object_key,
        filename=explanation.attachment_name or "lab-image",
        content_type=explanation.attachment_content_type,
    )
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.patch("/portal-explanations/{explanation_id}", response_model=AdminPortalExplanationRead)
def update_portal_explanation(
    explanation_id: str,
    payload: AdminPortalExplanationUpdate,
    db: DbSession,
    user: User = Depends(require_permission("admin:portal_uploads")),
) -> AdminPortalExplanationRead:
    explanation = db.scalar(
        select(PatientPortalExplanation)
        .options(selectinload(PatientPortalExplanation.patient))
        .where(
            PatientPortalExplanation.id == explanation_id,
            PatientPortalExplanation.organization_id == user.organization_id,
        )
    )
    if not explanation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portal explanation not found")
    before = {"extraction_status": explanation.extraction_status, "safety_status": explanation.safety_status}
    data = payload.model_dump(exclude_unset=True)
    if "extraction_status" in data:
        explanation.extraction_status = data["extraction_status"]
    if "safety_status" in data:
        explanation.safety_status = data["safety_status"]
    write_audit(db, user=user, action="admin.portal_explanation.update", entity_type="patient_portal_explanation", entity_id=explanation.id, before=before, after=data)
    db.commit()
    db.refresh(explanation)
    return to_admin_portal_explanation(explanation)


def count_model(db: DbSession, model, *criteria) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0


def to_admin_portal_explanation(explanation: PatientPortalExplanation) -> AdminPortalExplanationRead:
    base = to_explanation_read(explanation)
    return AdminPortalExplanationRead(
        **base.model_dump(),
        patient_name=explanation.patient.name,
        patient_medical_record_no=explanation.patient.medical_record_no,
    )
