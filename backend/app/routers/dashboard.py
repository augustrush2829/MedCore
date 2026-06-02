from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.models import ClinicalCase, LabResult, Medication, Patient, User
from app.dependencies import DbSession, require_permission

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def serialize_case(case: ClinicalCase) -> dict:
    patient = case.patient
    return {
        "id": case.id,
        "patientId": case.patient_id,
        "patientName": patient.name if patient else "",
        "chiefComplaint": case.chief_complaint,
        "status": case.status,
        "createdAt": case.created_at.isoformat(),
        "updatedAt": case.updated_at.isoformat(),
        "hasRedFlag": case.has_red_flag,
        "symptoms": [
            {
                "id": symptom.id,
                "name": symptom.name,
                "severity": symptom.severity,
                "onsetDate": symptom.onset_date.isoformat() if symptom.onset_date else "",
                "duration": symptom.duration or "",
                "note": symptom.note,
            }
            for symptom in case.symptoms
        ],
        "labResults": [
            {
                "id": lab.id,
                "testName": lab.test_name,
                "value": lab.value,
                "unit": lab.unit,
                "referenceRangeLow": lab.reference_low,
                "referenceRangeHigh": lab.reference_high,
                "abnormalFlag": lab.abnormal_flag,
                "collectedAt": lab.collected_at.isoformat(),
            }
            for lab in case.lab_results
        ],
        "medications": [
            {
                "id": medication.id,
                "name": medication.name,
                "dose": medication.dose,
                "route": medication.route,
                "frequency": medication.frequency,
                "startDate": medication.start_date.isoformat() if medication.start_date else "",
                "ingredients": [ingredient.ingredient_name for ingredient in medication.ingredients],
                "status": medication.status,
            }
            for medication in case.medications
        ],
        "attachments": [],
    }


@router.get("")
def dashboard(db: DbSession, user: User = Depends(require_permission("me:read"))) -> dict:
    today = date.today()
    base_filter = ClinicalCase.organization_id == user.organization_id
    cases_total = db.scalar(select(func.count()).select_from(ClinicalCase).where(base_filter)) or 0
    patients_total = db.scalar(select(func.count()).select_from(Patient).where(Patient.organization_id == user.organization_id)) or 0
    today_cases = db.scalar(select(func.count()).select_from(ClinicalCase).where(base_filter, func.date(ClinicalCase.created_at) == today)) or 0
    ai_complete = db.scalar(select(func.count()).select_from(ClinicalCase).where(base_filter, ClinicalCase.status == "ai_complete")) or 0
    red_flags = db.scalar(select(func.count()).select_from(ClinicalCase).where(base_filter, ClinicalCase.has_red_flag.is_(True))) or 0

    cases = db.scalars(
        select(ClinicalCase)
        .options(
            selectinload(ClinicalCase.patient),
            selectinload(ClinicalCase.symptoms),
            selectinload(ClinicalCase.lab_results),
            selectinload(ClinicalCase.medications).selectinload(Medication.ingredients),
        )
        .where(base_filter)
        .order_by(ClinicalCase.created_at.desc())
        .limit(10)
    ).all()

    return {
        "currentUser": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "organization": user.organization.name if user.organization else "",
            "specialty": "",
        },
        "stats": {
            "todayCases": today_cases,
            "newCases": cases_total,
            "aiComplete": ai_complete,
            "redFlags": red_flags,
            "patients": patients_total,
        },
        "cases": [serialize_case(case) for case in cases],
    }

