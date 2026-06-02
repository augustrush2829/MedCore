from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import CaseAttachment, ClinicalCase, Encounter, KnowledgeChunk, LabResult, ProposedClinicalFact, User
from app.routers.cases import apply_proposed_fact
from app.services.ai import build_rag_ai_content
from app.services.clinical_extraction import extract_attachment_to_proposed_facts
from app.services.image_storage import store_patient_file
from app.services.knowledge import ingest_knowledge_path

from conftest import get_patient_id


PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADElEQVR42mP8z8AARQADeQH9zQAAAABJRU5ErkJggg=="
)


def create_db_case(db_session) -> tuple[ClinicalCase, User]:
    doctor = db_session.scalar(select(User).where(User.email == "doctor@test.mn"))
    assert doctor is not None
    patient_id = get_patient_id("MR-A-001")
    encounter = Encounter(organization_id=doctor.organization_id, patient_id=patient_id, doctor_id=doctor.id)
    db_session.add(encounter)
    db_session.flush()
    case = ClinicalCase(
        organization_id=doctor.organization_id,
        encounter_id=encounter.id,
        patient_id=patient_id,
        created_by=doctor.id,
        chief_complaint="ALT өссөн, atorvastatin хэрэглэдэг",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case, doctor


def test_knowledge_ingest_is_idempotent_and_rag_fallback_uses_citations(tmp_path: Path, db_session):
    kb = tmp_path / "medical_kb"
    kb.mkdir()
    (kb / "statin_dili.md").write_text(
        "Statin adverse effect: ALT AST elevation can suggest drug-induced liver injury and requires review.",
        encoding="utf-8",
    )

    first = ingest_knowledge_path(db_session, kb, category="medication", version="test")
    second = ingest_knowledge_path(db_session, kb, category="medication", version="test")

    assert first["documents"] == 1
    assert first["chunks"] == 1
    assert second["skipped"] == 1
    assert db_session.scalar(select(KnowledgeChunk)) is not None

    case, _ = create_db_case(db_session)
    content = build_rag_ai_content(db_session, case, request_type="differential_diagnosis")

    assert content.doctor_confirmation_required is True
    assert content.citations[0].title == "statin dili"


def test_attachment_extraction_requires_review_without_gemini_key(db_session):
    case, doctor = create_db_case(db_session)
    stored = store_patient_file(organization_id=doctor.organization_id, patient_id=case.patient_id, data_url=PNG_DATA_URL)
    attachment = CaseAttachment(
        organization_id=doctor.organization_id,
        case_id=case.id,
        patient_id=case.patient_id,
        section="labs",
        file_name="lab.png",
        content_type=stored.content_type,
        object_key=stored.object_key,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        width=stored.width,
        height=stored.height,
    )
    db_session.add(attachment)
    db_session.commit()

    extraction = extract_attachment_to_proposed_facts(db_session, user=doctor, case=case, attachment=attachment)

    assert extraction.status == "requires_review"
    assert "GEMINI_API_KEY" in extraction.notes[0]
    assert attachment.extraction_status == "requires_review"


def test_approving_lab_proposed_fact_requires_date_then_creates_lab(db_session):
    case, doctor = create_db_case(db_session)
    fact = ProposedClinicalFact(
        organization_id=doctor.organization_id,
        case_id=case.id,
        patient_id=case.patient_id,
        fact_type="lab",
        fact_json={
            "test_name": "ALT",
            "value": 88,
            "unit": "U/L",
            "reference_low": 7,
            "reference_high": 40,
            "abnormal_flag": True,
            "collected_at": "",
            "date_review_required": True,
        },
        confidence=80,
    )
    db_session.add(fact)
    db_session.commit()

    with pytest.raises(HTTPException):
        apply_proposed_fact(db_session, case, fact, fact.fact_json)

    apply_proposed_fact(db_session, case, fact, {**fact.fact_json, "collected_at": "2026-06-02"})
    db_session.commit()

    lab = db_session.scalar(select(LabResult).where(LabResult.case_id == case.id, LabResult.test_name == "ALT"))
    assert lab is not None
    assert lab.collected_at.isoformat() == "2026-06-02"
