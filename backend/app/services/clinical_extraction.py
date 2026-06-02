import base64
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import CaseAttachment, ClinicalCase, DocumentExtraction, ProposedClinicalFact, User
from app.services.gemini import gemini_configured, generate_json
from app.services.image_storage import read_patient_image


EXTRACTION_VERSION = "medcore-clinical-extraction-gemini-v1"


def extract_attachment_to_proposed_facts(
    db: Session,
    *,
    user: User,
    case: ClinicalCase,
    attachment: CaseAttachment,
) -> DocumentExtraction:
    if not gemini_configured():
        extraction = DocumentExtraction(
            organization_id=user.organization_id,
            case_id=case.id,
            attachment_id=attachment.id,
            model=EXTRACTION_VERSION,
            status="requires_review",
            result_json={"facts": []},
            notes=["GEMINI_API_KEY тохируулагдаагүй тул автомат extraction хийгдээгүй."],
        )
        attachment.extraction_status = "requires_review"
        db.add(extraction)
        db.flush()
        return extraction

    data = read_patient_image(attachment.object_key)
    image = {"mime_type": attachment.content_type, "base64": base64.b64encode(data).decode("ascii")}
    result = generate_json(
        extraction_prompt(case, attachment),
        system_instruction=extraction_system_instruction(),
        image=image,
        timeout_seconds=90,
    )
    facts = normalize_facts(result.get("facts", []))
    extraction = DocumentExtraction(
        organization_id=user.organization_id,
        case_id=case.id,
        attachment_id=attachment.id,
        model=EXTRACTION_VERSION,
        status="requires_review",
        raw_text=result.get("raw_text"),
        result_json={"facts": facts, "document_date": result.get("document_date")},
        notes=result.get("notes") if isinstance(result.get("notes"), list) else ["Gemini extraction completed; doctor review required."],
    )
    db.add(extraction)
    db.flush()
    for fact in facts:
        db.add(
            ProposedClinicalFact(
                organization_id=user.organization_id,
                case_id=case.id,
                patient_id=case.patient_id,
                attachment_id=attachment.id,
                extraction_id=extraction.id,
                fact_type=fact["type"],
                fact_json=fact["data"],
                source_text=fact.get("source_text"),
                confidence=int(fact.get("confidence") or 50),
                status="pending_review",
            )
        )
    attachment.extraction_status = "requires_review"
    return extraction


def extraction_system_instruction() -> str:
    return """You extract structured clinical facts from medical images and PDFs.
Do not diagnose. Do not invent missing dates, medication use, lab values, allergies, or symptoms.
Return Mongolian or source-language names as visible in the document.
All extracted facts are proposed facts and require doctor review."""


def extraction_prompt(case: ClinicalCase, attachment: CaseAttachment) -> str:
    return f"""Extract structured clinical facts from this attachment.

Case chief complaint: {case.chief_complaint}
Attachment section: {attachment.section}
Attachment file name: {attachment.file_name}

Return JSON:
{{
  "raw_text": "all readable text, or null",
  "document_date": "YYYY-MM-DD or null",
  "facts": [
    {{
      "type": "lab|medication|allergy|symptom|diagnosis_hint",
      "confidence": 0,
      "source_text": "short quote from document",
      "data": {{
        "test_name": "ALT",
        "value": 48,
        "unit": "U/L",
        "reference_low": 7,
        "reference_high": 40,
        "abnormal_flag": true,
        "collected_at": "YYYY-MM-DD or empty string",
        "date_review_required": true
      }}
    }}
  ],
  "notes": ["missing date or unreadable areas"]
}}

Rules:
- For labs, use Date Collected/Collected date/Report date if clearly present. If no date exists, set collected_at="" and date_review_required=true.
- For medications, include name, dose, route, frequency, status, start_date, ingredients when visible.
- For allergies, include substance, reaction, severity when visible.
- For symptoms, severity must be mild, moderate, or severe when clear; otherwise omit severity.
- diagnosis_hint is informational only and must not become final diagnosis."""


def normalize_facts(raw_facts: object) -> list[dict]:
    if not isinstance(raw_facts, list):
        return []
    normalized: list[dict] = []
    for item in raw_facts:
        if not isinstance(item, dict):
            continue
        fact_type = item.get("type")
        if fact_type not in {"lab", "medication", "allergy", "symptom", "diagnosis_hint"}:
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        if fact_type == "lab":
            data = normalize_lab_data(data)
        normalized.append(
            {
                "type": fact_type,
                "confidence": max(0, min(100, int(item.get("confidence") or 50))),
                "source_text": item.get("source_text"),
                "data": data,
            }
        )
    return normalized


def normalize_lab_data(data: dict) -> dict:
    collected_at = normalize_date(data.get("collected_at"))
    return {
        "test_name": data.get("test_name") or "Unknown lab",
        "value": data.get("value"),
        "unit": data.get("unit") or "",
        "reference_low": data.get("reference_low"),
        "reference_high": data.get("reference_high"),
        "abnormal_flag": bool(data.get("abnormal_flag")),
        "collected_at": collected_at or "",
        "date_review_required": not bool(collected_at),
    }


def normalize_date(value: object) -> str | None:
    if not value:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None
