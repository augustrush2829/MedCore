from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, verify_password
from app.db.models import PatientPortalAccount, PatientPortalExplanation
from app.dependencies import CurrentPatientAccount, DbSession
from app.schemas import (
    PatientExplanationContent,
    PatientExplanationCreate,
    PatientExplanationRead,
    ImageExtractionResult,
    PatientPortalLoginRequest,
    PatientPortalLoginResponse,
    PatientPortalUserRead,
)
from app.services.patient_ai import build_patient_explanation, process_lab_image
from app.services.image_storage import patient_image_path, read_patient_image, store_patient_image

router = APIRouter(prefix="/patient-portal", tags=["patient-portal"])


def to_patient_read(account: PatientPortalAccount) -> PatientPortalUserRead:
    return PatientPortalUserRead(
        id=account.patient.id,
        name=account.patient.name,
        medical_record_no=account.patient.medical_record_no,
        organization_id=account.organization_id,
    )


def to_explanation_read(explanation: PatientPortalExplanation) -> PatientExplanationRead:
    return PatientExplanationRead(
        id=explanation.id,
        patient_id=explanation.patient_id,
        diagnosis_text=explanation.diagnosis_text,
        lab_name=explanation.lab_name,
        lab_value=explanation.lab_value,
        lab_unit=explanation.lab_unit,
        reference_range=explanation.reference_range,
        lab_collected_at=explanation.lab_collected_at,
        attachment_name=explanation.attachment_name,
        attachment_content_type=explanation.attachment_content_type,
        attachment_data_url=None,
        attachment_object_key=None,
        attachment_sha256=explanation.attachment_sha256,
        attachment_size_bytes=explanation.attachment_size_bytes,
        attachment_width=explanation.attachment_width,
        attachment_height=explanation.attachment_height,
        has_attachment=bool(explanation.attachment_object_key),
        patient_question=explanation.patient_question,
        extracted_lab_data=ImageExtractionResult.model_validate(explanation.extracted_lab_data),
        extraction_status=explanation.extraction_status,
        extraction_model=explanation.extraction_model,
        content=PatientExplanationContent.model_validate(explanation.explanation_json),
        safety_status=explanation.safety_status,
        created_at=explanation.created_at,
    )


@router.post("/login", response_model=PatientPortalLoginResponse)
def login_patient(payload: PatientPortalLoginRequest, db: DbSession) -> PatientPortalLoginResponse:
    account = db.scalar(
        select(PatientPortalAccount)
        .options(selectinload(PatientPortalAccount.patient))
        .where(PatientPortalAccount.login_identifier == payload.login_identifier, PatientPortalAccount.status == "active")
    )
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid patient credentials")
    account.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token(
        account.id,
        {"actor_type": "patient", "organization_id": account.organization_id, "patient_id": account.patient_id},
    )
    return PatientPortalLoginResponse(access_token=token, patient=to_patient_read(account))


@router.get("/me", response_model=PatientPortalUserRead)
def patient_me(account: CurrentPatientAccount) -> PatientPortalUserRead:
    return to_patient_read(account)


@router.get("/explanations", response_model=list[PatientExplanationRead])
def list_explanations(db: DbSession, account: CurrentPatientAccount) -> list[PatientExplanationRead]:
    explanations = db.scalars(
        select(PatientPortalExplanation)
        .where(
            PatientPortalExplanation.organization_id == account.organization_id,
            PatientPortalExplanation.patient_id == account.patient_id,
        )
        .order_by(PatientPortalExplanation.created_at.desc())
        .limit(50)
    ).all()
    return [to_explanation_read(explanation) for explanation in explanations]


@router.get("/explanations/{explanation_id}", response_model=PatientExplanationRead)
def get_explanation(explanation_id: str, db: DbSession, account: CurrentPatientAccount) -> PatientExplanationRead:
    explanation = db.get(PatientPortalExplanation, explanation_id)
    if (
        not explanation
        or explanation.organization_id != account.organization_id
        or explanation.patient_id != account.patient_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Explanation not found")
    return to_explanation_read(explanation)


@router.get("/explanations/{explanation_id}/image")
def get_explanation_image(explanation_id: str, db: DbSession, account: CurrentPatientAccount) -> Response:
    explanation = db.get(PatientPortalExplanation, explanation_id)
    if (
        not explanation
        or explanation.organization_id != account.organization_id
        or explanation.patient_id != account.patient_id
        or not explanation.attachment_object_key
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    try:
        path = patient_image_path(explanation.attachment_object_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found") from exc
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return Response(
        content=read_patient_image(explanation.attachment_object_key),
        media_type=explanation.attachment_content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{explanation.attachment_name or "lab-image"}"'},
    )


@router.post("/explanations", response_model=PatientExplanationRead, status_code=status.HTTP_201_CREATED)
def create_explanation(
    payload: PatientExplanationCreate,
    db: DbSession,
    account: CurrentPatientAccount,
) -> PatientExplanationRead:
    stored_image = None
    if payload.attachment_data_url:
        try:
            stored_image = store_patient_image(
                organization_id=account.organization_id,
                patient_id=account.patient_id,
                data_url=payload.attachment_data_url,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    extraction = process_lab_image(payload, stored_image)
    content = build_patient_explanation(payload)
    explanation = PatientPortalExplanation(
        organization_id=account.organization_id,
        patient_id=account.patient_id,
        diagnosis_text=payload.diagnosis_text,
        lab_name=payload.lab_name,
        lab_value=payload.lab_value,
        lab_unit=payload.lab_unit,
        reference_range=payload.reference_range,
        lab_collected_at=payload.lab_collected_at,
        attachment_name=payload.attachment_name,
        attachment_content_type=stored_image.content_type if stored_image else payload.attachment_content_type,
        attachment_object_key=stored_image.object_key if stored_image else None,
        attachment_sha256=stored_image.sha256 if stored_image else None,
        attachment_size_bytes=stored_image.size_bytes if stored_image else None,
        attachment_width=stored_image.width if stored_image else None,
        attachment_height=stored_image.height if stored_image else None,
        attachment_data_url=None,
        extracted_lab_data=extraction.model_dump(),
        extraction_status=extraction.status,
        extraction_model=extraction.model,
        patient_question=payload.patient_question,
        explanation_json=content.model_dump(),
    )
    db.add(explanation)
    db.commit()
    db.refresh(explanation)
    return to_explanation_read(explanation)
