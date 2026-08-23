import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import CaseAttachment, ClinicalCase, Encounter, KnowledgeChunk, LabResult, ProposedClinicalFact, User
from app.routers.cases import apply_proposed_fact
from app.services.ai import build_rag_ai_content
from app.services.clinical_extraction import extract_attachment_to_proposed_facts
from app.services.image_storage import store_patient_file
from app.services.knowledge import ingest_knowledge_path, retrieve_context

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


def ingest_statin_dili_chunk(tmp_path: Path, db_session) -> None:
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


def test_knowledge_ingest_is_idempotent_and_rag_fallback_uses_citations(tmp_path: Path, db_session, monkeypatch):
    ingest_statin_dili_chunk(tmp_path, db_session)

    def fake_generate_json(*args, **kwargs):
        raise RuntimeError("Ollama сервертэй холбогдож чадсангүй")

    monkeypatch.setattr("app.services.ai.generate_json", fake_generate_json)

    case, _ = create_db_case(db_session)
    content = build_rag_ai_content(db_session, case, request_type="differential_diagnosis")

    assert content.doctor_confirmation_required is True
    assert content.citations[0].title == "statin dili"
    assert "Local LLM/RAG analyze fallback" in content.missing_information[-1]


def test_rag_ai_content_uses_local_llm_result_when_available(tmp_path: Path, db_session, monkeypatch):
    ingest_statin_dili_chunk(tmp_path, db_session)

    def fake_generate_json(*args, **kwargs):
        return {
            "clinical_summary": "Local LLM summary",
            "differential_diagnosis": [
                {
                    "name": "Drug-induced liver injury",
                    "confidence": 70,
                    "supporting_evidence": ["ALT elevated"],
                    "missing_evidence": ["Ultrasound"],
                    "icd_code": "K71",
                }
            ],
            "missing_information": ["Baseline liver panel"],
            "recommended_tests": [{"name": "ALP, GGT", "reason": "Cholestatic pattern", "priority": "routine"}],
            "medication_warnings": [],
            "causality_assessment": {"type": "medication_related", "confidence": 65, "evidence": "Statin timeline overlaps"},
            "red_flags": [],
            "citations": [],
            "confidence_level": 60,
            "doctor_confirmation_required": True,
        }

    monkeypatch.setattr("app.services.ai.generate_json", fake_generate_json)

    case, _ = create_db_case(db_session)
    content = build_rag_ai_content(db_session, case, request_type="differential_diagnosis")

    assert content.clinical_summary == "Local LLM summary"
    assert content.doctor_confirmation_required is True
    assert content.citations[0].title == "statin dili"


def test_json_record_list_ingests_one_chunk_per_record_with_own_title(tmp_path: Path, db_session):
    kb = tmp_path / "mn_edoctor_kb"
    kb.mkdir()
    (kb / "edoctor_sample.json").write_text(
        json.dumps(
            [
                {"Өвчин": "Аденовируст халдвар", "Тайлбар": "Амьсгалын замын цочмог халдварт өвчин."},
                {"Өвчин": "Алцхеймерийн өвчин", "Тайлбар": "Тархины эсүүд аажмаар үхэж, ой санамж буурдаг."},
            ]
        ),
        encoding="utf-8",
    )

    result = ingest_knowledge_path(db_session, kb, category="clinical", version="test")

    assert result["documents"] == 1
    assert result["chunks"] == 2

    chunks = list(db_session.scalars(select(KnowledgeChunk).order_by(KnowledgeChunk.chunk_index)))
    assert [chunk.source_title for chunk in chunks] == ["Аденовируст халдвар", "Алцхеймерийн өвчин"]
    assert "цочмог халдварт" in chunks[0].content

    retrieved = retrieve_context(db_session, "Алцхеймерийн өвчин ой санамж", top_k=1)
    assert retrieved[0].source_title == "Алцхеймерийн өвчин"


def create_case_attachment(db_session, case, doctor) -> CaseAttachment:
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
    return attachment


def test_attachment_extraction_requires_review_when_local_llm_unavailable(db_session, monkeypatch):
    case, doctor = create_db_case(db_session)
    attachment = create_case_attachment(db_session, case, doctor)

    def fake_generate_json(*args, **kwargs):
        raise RuntimeError("Ollama сервертэй холбогдож чадсангүй")

    monkeypatch.setattr("app.services.clinical_extraction.generate_json", fake_generate_json)

    extraction = extract_attachment_to_proposed_facts(db_session, user=doctor, case=case, attachment=attachment)

    assert extraction.status == "requires_review"
    assert "Ollama" in extraction.notes[0]
    assert attachment.extraction_status == "requires_review"


def test_attachment_extraction_creates_proposed_facts_from_local_llm(db_session, monkeypatch):
    case, doctor = create_db_case(db_session)
    attachment = create_case_attachment(db_session, case, doctor)

    def fake_generate_json(*args, **kwargs):
        return {
            "raw_text": "ALT 88 U/L",
            "document_date": "2026-06-01",
            "facts": [
                {
                    "type": "lab",
                    "confidence": 90,
                    "source_text": "ALT 88",
                    "data": {
                        "test_name": "ALT",
                        "value": 88,
                        "unit": "U/L",
                        "reference_low": 7,
                        "reference_high": 40,
                        "abnormal_flag": True,
                        "collected_at": "2026-06-01",
                    },
                }
            ],
            "notes": [],
        }

    monkeypatch.setattr("app.services.clinical_extraction.generate_json", fake_generate_json)

    extraction = extract_attachment_to_proposed_facts(db_session, user=doctor, case=case, attachment=attachment)
    db_session.commit()

    assert extraction.status == "requires_review"
    assert attachment.extraction_status == "requires_review"
    proposed = db_session.scalar(select(ProposedClinicalFact).where(ProposedClinicalFact.extraction_id == extraction.id))
    assert proposed is not None
    assert proposed.fact_json["test_name"] == "ALT"


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
