from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import (
    AIRequest,
    AIResponse,
    ClinicalCase,
    DoctorDecision,
    DoctorFeedbackEvent,
    Encounter,
    LabResult,
    Medication,
    MedicationIngredient,
    Patient,
    Supplement,
    Symptom,
    User,
    VitalSign,
)
from app.dependencies import DbSession, require_permission
from app.schemas import (
    AIContent,
    AIResponseRead,
    ClinicalCaseCreate,
    ClinicalCaseRead,
    DoctorDecisionCreate,
    DoctorDecisionRead,
    FeedbackCreate,
    LabResultCreate,
    MedicationCreate,
    MedicationWarning,
    CausalityAssessment,
    SupplementCreate,
    SymptomCreate,
    VitalSignCreate,
)
from app.services.ai import build_ai_content
from app.services.audit import write_audit

router = APIRouter(prefix="/cases", tags=["cases"])


def case_options():
    return (
        selectinload(ClinicalCase.symptoms),
        selectinload(ClinicalCase.vital_signs),
        selectinload(ClinicalCase.lab_results),
        selectinload(ClinicalCase.medications).selectinload(Medication.ingredients),
        selectinload(ClinicalCase.supplements),
        selectinload(ClinicalCase.patient).selectinload(Patient.allergies),
    )


def load_case(db: DbSession, case_id: str, organization_id: str) -> ClinicalCase:
    case = db.scalar(select(ClinicalCase).options(*case_options()).where(ClinicalCase.id == case_id))
    if not case or case.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def persist_ai_response(
    db: DbSession,
    *,
    user: User,
    case: ClinicalCase,
    request_type: str,
) -> tuple[AIResponse, AIContent]:
    case.status = "ai_pending"
    request = AIRequest(organization_id=user.organization_id, case_id=case.id, request_type=request_type)
    db.add(request)
    db.flush()

    content = build_ai_content(case)
    response = AIResponse(
        organization_id=user.organization_id,
        case_id=case.id,
        request_id=request.id,
        response_type=request_type,
        content_json=content.model_dump(),
        confidence=content.confidence_level,
    )
    case.status = "ai_complete"
    case.has_red_flag = bool(content.red_flags)
    db.add(response)
    write_audit(
        db,
        user=user,
        action=f"ai.{request_type}.create",
        entity_type="case",
        entity_id=case.id,
        after={"ai_response_id": response.id, "confidence": content.confidence_level},
    )
    db.commit()
    db.refresh(response)
    return response, content


def to_ai_response_read(response: AIResponse) -> AIResponseRead:
    return AIResponseRead(
        id=response.id,
        case_id=response.case_id,
        request_id=response.request_id,
        response_type=response.response_type,
        content=AIContent.model_validate(response.content_json),
        confidence=response.confidence,
        safety_status=response.safety_status,
        model_version=response.model_version,
        generated_at=response.generated_at,
    )


@router.get("", response_model=list[ClinicalCaseRead])
def list_cases(
    db: DbSession,
    user: User = Depends(require_permission("case:read")),
) -> list[ClinicalCase]:
    return list(
        db.scalars(
            select(ClinicalCase)
            .options(*case_options())
            .where(ClinicalCase.organization_id == user.organization_id)
            .order_by(ClinicalCase.created_at.desc())
            .limit(100)
        ).all()
    )


@router.post("", response_model=ClinicalCaseRead, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: ClinicalCaseCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:create")),
) -> ClinicalCase:
    patient = db.get(Patient, payload.patient_id)
    if not patient or patient.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    encounter = Encounter(organization_id=user.organization_id, patient_id=patient.id, doctor_id=user.id)
    db.add(encounter)
    db.flush()
    case = ClinicalCase(
        organization_id=user.organization_id,
        encounter_id=encounter.id,
        patient_id=patient.id,
        created_by=user.id,
        chief_complaint=payload.chief_complaint,
        notes=payload.notes,
    )
    db.add(case)
    db.flush()
    write_audit(db, user=user, action="case.create", entity_type="case", entity_id=case.id, after=payload.model_dump())
    db.commit()
    return load_case(db, case.id, user.organization_id)


@router.get("/{case_id}", response_model=ClinicalCaseRead)
def get_case(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("case:read")),
) -> ClinicalCase:
    case = load_case(db, case_id, user.organization_id)
    write_audit(db, user=user, action="case.view", entity_type="case", entity_id=case.id)
    db.commit()
    return case


@router.post("/{case_id}/symptoms", response_model=ClinicalCaseRead, status_code=status.HTTP_201_CREATED)
def add_symptom(
    case_id: str,
    payload: SymptomCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> ClinicalCase:
    case = load_case(db, case_id, user.organization_id)
    db.add(Symptom(case_id=case.id, **payload.model_dump()))
    write_audit(db, user=user, action="case.symptom.create", entity_type="case", entity_id=case.id, after=payload.model_dump())
    db.commit()
    return load_case(db, case.id, user.organization_id)


@router.post("/{case_id}/vitals", response_model=ClinicalCaseRead, status_code=status.HTTP_201_CREATED)
def add_vital(
    case_id: str,
    payload: VitalSignCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> ClinicalCase:
    case = load_case(db, case_id, user.organization_id)
    data = payload.model_dump()
    if data["measured_at"] is None:
        data.pop("measured_at")
    db.add(VitalSign(case_id=case.id, **data))
    write_audit(db, user=user, action="case.vital.create", entity_type="case", entity_id=case.id, after=payload.model_dump())
    db.commit()
    return load_case(db, case.id, user.organization_id)


@router.post("/{case_id}/labs", response_model=ClinicalCaseRead, status_code=status.HTTP_201_CREATED)
def add_lab(
    case_id: str,
    payload: LabResultCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> ClinicalCase:
    case = load_case(db, case_id, user.organization_id)
    db.add(LabResult(case_id=case.id, **payload.model_dump()))
    write_audit(db, user=user, action="case.lab.create", entity_type="case", entity_id=case.id, after=payload.model_dump())
    db.commit()
    return load_case(db, case.id, user.organization_id)


@router.post("/{case_id}/medications", response_model=ClinicalCaseRead, status_code=status.HTTP_201_CREATED)
def add_medication(
    case_id: str,
    payload: MedicationCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> ClinicalCase:
    case = load_case(db, case_id, user.organization_id)
    data = payload.model_dump()
    ingredient_payloads = data.pop("ingredients")
    medication = Medication(case_id=case.id, **data)
    medication.ingredients = [MedicationIngredient(**ingredient) for ingredient in ingredient_payloads]
    db.add(medication)
    write_audit(db, user=user, action="case.medication.create", entity_type="case", entity_id=case.id, after=payload.model_dump())
    db.commit()
    return load_case(db, case.id, user.organization_id)


@router.post("/{case_id}/supplements", response_model=ClinicalCaseRead, status_code=status.HTTP_201_CREATED)
def add_supplement(
    case_id: str,
    payload: SupplementCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> ClinicalCase:
    case = load_case(db, case_id, user.organization_id)
    db.add(Supplement(case_id=case.id, **payload.model_dump()))
    write_audit(db, user=user, action="case.supplement.create", entity_type="case", entity_id=case.id, after=payload.model_dump())
    db.commit()
    return load_case(db, case.id, user.organization_id)


@router.post("/{case_id}/ai/differential-diagnosis", response_model=AIResponseRead)
def run_ai_analysis(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("ai:run")),
) -> AIResponseRead:
    case = load_case(db, case_id, user.organization_id)
    response, _ = persist_ai_response(db, user=user, case=case, request_type="differential_diagnosis")
    return to_ai_response_read(response)


@router.post("/{case_id}/ai/lab-interpretation", response_model=AIResponseRead)
def run_lab_interpretation(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("ai:run")),
) -> AIResponseRead:
    case = load_case(db, case_id, user.organization_id)
    response, _ = persist_ai_response(db, user=user, case=case, request_type="lab_interpretation")
    return to_ai_response_read(response)


@router.post("/{case_id}/ai/medication-check", response_model=list[MedicationWarning])
def run_medication_check(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("ai:medication_check")),
) -> list[MedicationWarning]:
    case = load_case(db, case_id, user.organization_id)
    response, content = persist_ai_response(db, user=user, case=case, request_type="medication_check")
    write_audit(
        db,
        user=user,
        action="ai.medication_warnings.view",
        entity_type="ai_response",
        entity_id=response.id,
        after={"warning_count": len(content.medication_warnings)},
    )
    db.commit()
    return content.medication_warnings


@router.post("/{case_id}/ai/causality-assessment", response_model=CausalityAssessment)
def run_causality_assessment(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("ai:run")),
) -> CausalityAssessment:
    case = load_case(db, case_id, user.organization_id)
    response, content = persist_ai_response(db, user=user, case=case, request_type="causality_assessment")
    write_audit(
        db,
        user=user,
        action="ai.causality.view",
        entity_type="ai_response",
        entity_id=response.id,
        after=content.causality_assessment.model_dump(),
    )
    db.commit()
    return content.causality_assessment


@router.post("/{case_id}/doctor-decision", response_model=DoctorDecisionRead, status_code=status.HTTP_201_CREATED)
def create_doctor_decision(
    case_id: str,
    payload: DoctorDecisionCreate,
    db: DbSession,
    user: User = Depends(require_permission("decision:create")),
) -> DoctorDecision:
    case = load_case(db, case_id, user.organization_id)
    ai_response = db.get(AIResponse, payload.ai_response_id)
    if not ai_response or ai_response.organization_id != user.organization_id or ai_response.case_id != case.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI response not found")
    decision = DoctorDecision(
        organization_id=user.organization_id,
        ai_response_id=ai_response.id,
        doctor_id=user.id,
        decision=payload.decision,
        final_note=payload.final_note,
    )
    case.status = "doctor_reviewed"
    db.add(decision)
    write_audit(db, user=user, action="doctor_decision.create", entity_type="case", entity_id=case.id, after=payload.model_dump())
    db.commit()
    db.refresh(decision)
    return decision


@router.post("/ai-responses/{ai_response_id}/feedback", status_code=status.HTTP_201_CREATED)
def create_feedback(
    ai_response_id: str,
    payload: FeedbackCreate,
    db: DbSession,
    user: User = Depends(require_permission("feedback:create")),
) -> dict:
    ai_response = db.get(AIResponse, ai_response_id)
    if not ai_response or ai_response.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI response not found")
    feedback = DoctorFeedbackEvent(
        organization_id=user.organization_id,
        ai_response_id=ai_response.id,
        doctor_id=user.id,
        **payload.model_dump(),
    )
    db.add(feedback)
    write_audit(db, user=user, action="ai.feedback.create", entity_type="ai_response", entity_id=ai_response.id, after=payload.model_dump())
    db.commit()
    return {"id": feedback.id, "status": "created"}
