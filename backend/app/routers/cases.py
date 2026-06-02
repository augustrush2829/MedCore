from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.db.models import (
    AIRequest,
    AIResponse,
    Allergy,
    CaseAttachment,
    ClinicalCase,
    DocumentExtraction,
    DoctorDecision,
    DoctorFeedbackEvent,
    Encounter,
    LabResult,
    Medication,
    MedicationIngredient,
    Patient,
    ProposedClinicalFact,
    Supplement,
    Symptom,
    User,
    VitalSign,
    utc_now,
)
from app.dependencies import DbSession, require_permission
from app.schemas import (
    AIContent,
    AIResponseRead,
    CaseAttachmentCreate,
    CaseAttachmentRead,
    ClinicalCaseCreate,
    DocumentExtractionRead,
    ClinicalCaseRead,
    ClinicalCaseUpdate,
    DoctorDecisionCreate,
    DoctorDecisionRead,
    FeedbackCreate,
    LabResultCreate,
    MedicationCreate,
    MedicationWarning,
    CausalityAssessment,
    ProposedClinicalFactRead,
    ProposedFactReview,
    SupplementCreate,
    SymptomCreate,
    VitalSignCreate,
)
from app.services.ai import RAG_PROMPT_VERSION, build_rag_ai_content
from app.services.audit import write_audit
from app.services.clinical_extraction import extract_attachment_to_proposed_facts
from app.services.image_storage import store_patient_file

router = APIRouter(prefix="/cases", tags=["cases"])


def case_options():
    return (
        selectinload(ClinicalCase.symptoms),
        selectinload(ClinicalCase.vital_signs),
        selectinload(ClinicalCase.lab_results),
        selectinload(ClinicalCase.medications).selectinload(Medication.ingredients),
        selectinload(ClinicalCase.supplements),
        selectinload(ClinicalCase.patient).selectinload(Patient.allergies),
        selectinload(ClinicalCase.attachments),
        selectinload(ClinicalCase.proposed_facts),
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
    request = AIRequest(
        organization_id=user.organization_id,
        case_id=case.id,
        request_type=request_type,
        model="gemini-rag",
        prompt_version=RAG_PROMPT_VERSION,
    )
    db.add(request)
    db.flush()

    content = build_rag_ai_content(db, case, request_type=request_type)
    response = AIResponse(
        organization_id=user.organization_id,
        case_id=case.id,
        request_id=request.id,
        response_type=request_type,
        content_json=content.model_dump(),
        confidence=content.confidence_level,
        model_version=RAG_PROMPT_VERSION,
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


def load_proposed_fact(db: DbSession, case: ClinicalCase, fact_id: str, organization_id: str) -> ProposedClinicalFact:
    fact = db.get(ProposedClinicalFact, fact_id)
    if not fact or fact.case_id != case.id or fact.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposed fact not found")
    if fact.status != "pending_review":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Proposed fact already reviewed")
    return fact


def apply_proposed_fact(db: DbSession, case: ClinicalCase, fact: ProposedClinicalFact, fact_data: dict) -> None:
    if fact.fact_type == "lab":
        collected_at = fact_data.get("collected_at")
        if not collected_at:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lab огноо байхгүй тул эмч collected_at бөглөж батална")
        try:
            collected_date = date.fromisoformat(collected_at) if isinstance(collected_at, str) else collected_at
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="collected_at YYYY-MM-DD форматтай байх ёстой") from exc
        db.add(
            LabResult(
                case_id=case.id,
                test_name=fact_data.get("test_name") or "Unknown lab",
                value=float(fact_data.get("value") or 0),
                unit=fact_data.get("unit") or "",
                reference_low=fact_data.get("reference_low"),
                reference_high=fact_data.get("reference_high"),
                abnormal_flag=bool(fact_data.get("abnormal_flag")),
                collected_at=collected_date,
            )
        )
    elif fact.fact_type == "medication":
        medication = Medication(
            case_id=case.id,
            name=fact_data.get("name") or "Unknown medication",
            dose=fact_data.get("dose") or "unknown",
            route=fact_data.get("route") or "unknown",
            frequency=fact_data.get("frequency") or "unknown",
            start_date=fact_data.get("start_date"),
            status=fact_data.get("status") or "active",
        )
        medication.ingredients = [
            MedicationIngredient(ingredient_name=str(ingredient))
            for ingredient in fact_data.get("ingredients", [])
            if str(ingredient).strip()
        ]
        db.add(medication)
    elif fact.fact_type == "symptom":
        db.add(
            Symptom(
                case_id=case.id,
                name=fact_data.get("name") or "Unknown symptom",
                severity=fact_data.get("severity") if fact_data.get("severity") in {"mild", "moderate", "severe"} else "mild",
                onset_date=fact_data.get("onset_date"),
                duration=fact_data.get("duration"),
                note=fact_data.get("note"),
            )
        )
    elif fact.fact_type == "allergy":
        db.add(
            Allergy(
                organization_id=case.organization_id,
                patient_id=case.patient_id,
                substance=fact_data.get("substance") or "Unknown allergy",
                reaction=fact_data.get("reaction"),
                severity=fact_data.get("severity") or "unknown",
                verified_status="doctor_verified",
            )
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


@router.put("/{case_id}", response_model=ClinicalCaseRead)
def update_case(
    case_id: str,
    payload: ClinicalCaseUpdate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> ClinicalCase:
    case = load_case(db, case_id, user.organization_id)
    before = {
        "chief_complaint": case.chief_complaint,
        "notes": case.notes,
        "status": case.status,
        "has_red_flag": case.has_red_flag,
    }
    data = payload.model_dump(exclude_unset=True)
    if "chief_complaint" in data:
        case.chief_complaint = data["chief_complaint"]
    if "notes" in data:
        case.notes = data["notes"]
    if "status" in data:
        case.status = data["status"]
    if "has_red_flag" in data:
        case.has_red_flag = data["has_red_flag"]
    case.updated_at = utc_now()
    write_audit(db, user=user, action="case.update", entity_type="case", entity_id=case.id, before=before, after=data)
    db.commit()
    return load_case(db, case.id, user.organization_id)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> None:
    case = load_case(db, case_id, user.organization_id)
    ai_responses = db.scalars(
        select(AIResponse).where(AIResponse.organization_id == user.organization_id, AIResponse.case_id == case.id)
    ).all()
    ai_response_ids = [response.id for response in ai_responses]
    request_ids = [response.request_id for response in ai_responses]
    if ai_response_ids:
        db.execute(delete(DoctorFeedbackEvent).where(DoctorFeedbackEvent.ai_response_id.in_(ai_response_ids)))
        db.execute(delete(DoctorDecision).where(DoctorDecision.ai_response_id.in_(ai_response_ids)))
        db.execute(delete(AIResponse).where(AIResponse.id.in_(ai_response_ids)))
    if request_ids:
        db.execute(delete(AIRequest).where(AIRequest.id.in_(request_ids)))
    write_audit(db, user=user, action="case.delete", entity_type="case", entity_id=case.id, before={"patient_id": case.patient_id, "status": case.status})
    db.delete(case)
    db.commit()
    return None


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


@router.post("/{case_id}/attachments", response_model=CaseAttachmentRead, status_code=status.HTTP_201_CREATED)
def create_case_attachment(
    case_id: str,
    payload: CaseAttachmentCreate,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> CaseAttachment:
    case = load_case(db, case_id, user.organization_id)
    try:
        stored = store_patient_file(organization_id=user.organization_id, patient_id=case.patient_id, data_url=payload.data_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    attachment = CaseAttachment(
        organization_id=user.organization_id,
        case_id=case.id,
        patient_id=case.patient_id,
        section=payload.section,
        file_name=payload.file_name,
        content_type=stored.content_type,
        object_key=stored.object_key,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        width=stored.width,
        height=stored.height,
    )
    db.add(attachment)
    write_audit(db, user=user, action="case.attachment.create", entity_type="case", entity_id=case.id, after={"file_name": payload.file_name, "section": payload.section})
    db.commit()
    db.refresh(attachment)
    return attachment


@router.post("/{case_id}/attachments/{attachment_id}/extract", response_model=DocumentExtractionRead)
def extract_case_attachment(
    case_id: str,
    attachment_id: str,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> DocumentExtraction:
    case = load_case(db, case_id, user.organization_id)
    attachment = db.get(CaseAttachment, attachment_id)
    if not attachment or attachment.case_id != case.id or attachment.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    extraction = extract_attachment_to_proposed_facts(db, user=user, case=case, attachment=attachment)
    write_audit(db, user=user, action="case.attachment.extract", entity_type="case_attachment", entity_id=attachment.id, after={"extraction_id": extraction.id, "status": extraction.status})
    db.commit()
    db.refresh(extraction)
    return extraction


@router.post("/{case_id}/extract-labs")
def extract_case_lab_attachments(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> dict:
    case = load_case(db, case_id, user.organization_id)
    lab_attachments = [attachment for attachment in case.attachments if attachment.section == "labs"]
    if not lab_attachments:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No lab attachments found")
    extractions = [
        extract_attachment_to_proposed_facts(db, user=user, case=case, attachment=attachment)
        for attachment in lab_attachments
    ]
    write_audit(
        db,
        user=user,
        action="case.lab_attachments.extract",
        entity_type="case",
        entity_id=case.id,
        after={"attachment_count": len(lab_attachments), "extraction_count": len(extractions)},
    )
    db.commit()
    refreshed_case = load_case(db, case.id, user.organization_id)
    return {
        "added": 0,
        "extracted": len(extractions),
        "patientLabsAdded": 0,
        "case": ClinicalCaseRead.model_validate(refreshed_case).model_dump(mode="json"),
        "extractions": [extraction.id for extraction in extractions],
    }


@router.get("/{case_id}/proposed-facts", response_model=list[ProposedClinicalFactRead])
def list_proposed_facts(
    case_id: str,
    db: DbSession,
    user: User = Depends(require_permission("case:read")),
) -> list[ProposedClinicalFact]:
    case = load_case(db, case_id, user.organization_id)
    return list(
        db.scalars(
            select(ProposedClinicalFact)
            .where(ProposedClinicalFact.case_id == case.id)
            .order_by(ProposedClinicalFact.created_at.desc())
        ).all()
    )


@router.post("/{case_id}/proposed-facts/{fact_id}/approve", response_model=ProposedClinicalFactRead)
def approve_proposed_fact(
    case_id: str,
    fact_id: str,
    payload: ProposedFactReview,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> ProposedClinicalFact:
    case = load_case(db, case_id, user.organization_id)
    fact = load_proposed_fact(db, case, fact_id, user.organization_id)
    fact_data = payload.fact_json or fact.fact_json
    apply_proposed_fact(db, case, fact, fact_data)
    fact.fact_json = fact_data
    fact.status = "approved"
    fact.reviewed_by = user.id
    fact.reviewed_at = utc_now()
    fact.review_note = payload.note
    write_audit(db, user=user, action="case.proposed_fact.approve", entity_type="proposed_clinical_fact", entity_id=fact.id, after=fact_data)
    db.commit()
    db.refresh(fact)
    return fact


@router.post("/{case_id}/proposed-facts/{fact_id}/reject", response_model=ProposedClinicalFactRead)
def reject_proposed_fact(
    case_id: str,
    fact_id: str,
    payload: ProposedFactReview,
    db: DbSession,
    user: User = Depends(require_permission("case:update")),
) -> ProposedClinicalFact:
    case = load_case(db, case_id, user.organization_id)
    fact = load_proposed_fact(db, case, fact_id, user.organization_id)
    fact.status = "rejected"
    fact.reviewed_by = user.id
    fact.reviewed_at = utc_now()
    fact.review_note = payload.note
    write_audit(db, user=user, action="case.proposed_fact.reject", entity_type="proposed_clinical_fact", entity_id=fact.id, after={"note": payload.note})
    db.commit()
    db.refresh(fact)
    return fact


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
