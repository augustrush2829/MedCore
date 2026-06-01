from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select

from app.db.models import Allergy, ClinicalCase, Patient, PatientVerifiedFact, User
from app.dependencies import DbSession, require_permission
from app.schemas import AllergyCreate, AllergyRead, PatientCreate, PatientRead, PatientVerifiedFactCreate, PatientVerifiedFactRead
from app.services.audit import write_audit

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientRead])
def list_patients(
    db: DbSession,
    user: User = Depends(require_permission("patient:read")),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Patient]:
    statement = select(Patient).where(Patient.organization_id == user.organization_id).order_by(Patient.created_at.desc()).limit(limit)
    if q:
        like = f"%{q}%"
        statement = (
            select(Patient)
            .where(
                Patient.organization_id == user.organization_id,
                or_(Patient.name.ilike(like), Patient.medical_record_no.ilike(like)),
            )
            .order_by(Patient.created_at.desc())
            .limit(limit)
        )
    return list(db.scalars(statement).all())


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: DbSession,
    user: User = Depends(require_permission("patient:create")),
) -> Patient:
    exists = db.scalar(
        select(Patient).where(
            Patient.organization_id == user.organization_id,
            Patient.medical_record_no == payload.medical_record_no,
        )
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Medical record number already exists")
    patient = Patient(organization_id=user.organization_id, **payload.model_dump())
    db.add(patient)
    db.flush()
    write_audit(db, user=user, action="patient.create", entity_type="patient", entity_id=patient.id, after=payload.model_dump())
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: str,
    db: DbSession,
    user: User = Depends(require_permission("patient:read")),
) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient or patient.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    write_audit(db, user=user, action="patient.view", entity_type="patient", entity_id=patient.id)
    db.commit()
    return patient


@router.post("/{patient_id}/allergies", response_model=AllergyRead, status_code=status.HTTP_201_CREATED)
def add_allergy(
    patient_id: str,
    payload: AllergyCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> Allergy:
    patient = db.get(Patient, patient_id)
    if not patient or patient.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    allergy = Allergy(organization_id=user.organization_id, patient_id=patient.id, **payload.model_dump())
    db.add(allergy)
    write_audit(db, user=user, action="allergy.create", entity_type="patient", entity_id=patient.id, after=payload.model_dump())
    db.commit()
    db.refresh(allergy)
    return allergy


@router.get("/{patient_id}/verified-facts", response_model=list[PatientVerifiedFactRead])
def list_verified_facts(
    patient_id: str,
    db: DbSession,
    user: User = Depends(require_permission("patient:read")),
) -> list[PatientVerifiedFact]:
    patient = db.get(Patient, patient_id)
    if not patient or patient.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return list(
        db.scalars(
            select(PatientVerifiedFact)
            .where(
                PatientVerifiedFact.organization_id == user.organization_id,
                PatientVerifiedFact.patient_id == patient.id,
            )
            .order_by(PatientVerifiedFact.verified_at.desc())
        ).all()
    )


@router.post("/{patient_id}/verified-facts", response_model=PatientVerifiedFactRead, status_code=status.HTTP_201_CREATED)
def create_verified_fact(
    patient_id: str,
    payload: PatientVerifiedFactCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> PatientVerifiedFact:
    patient = db.get(Patient, patient_id)
    if not patient or patient.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if payload.source_case_id:
        source_case = db.get(ClinicalCase, payload.source_case_id)
        if not source_case or source_case.organization_id != user.organization_id or source_case.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source case not found")
    fact = PatientVerifiedFact(
        organization_id=user.organization_id,
        patient_id=patient.id,
        verified_by=user.id,
        **payload.model_dump(),
    )
    db.add(fact)
    write_audit(db, user=user, action="patient_verified_fact.create", entity_type="patient", entity_id=patient.id, after=payload.model_dump())
    db.commit()
    db.refresh(fact)
    return fact
