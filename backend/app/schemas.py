from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


Gender = Literal["male", "female", "other"]
Severity = Literal["mild", "moderate", "severe", "unknown"]
CaseStatus = Literal["draft", "ai_pending", "ai_complete", "doctor_reviewed", "finalized"]
DecisionValue = Literal["accept", "edit", "reject"]


class UserRead(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    organization_id: str
    organization_name: str | None = None


class AdminUserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=255)
    role: Literal["doctor", "pharmacist", "admin", "auditor"] = "doctor"
    password: str = Field(min_length=6)


class AdminUserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    role: Literal["doctor", "pharmacist", "admin", "auditor"] | None = None
    status: Literal["active", "disabled"] | None = None


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    plan: str
    status: str
    settings: dict
    created_at: datetime
    updated_at: datetime


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    plan: str = Field(default="mvp", max_length=50)
    status: Literal["active", "disabled"] = "active"
    settings: dict = Field(default_factory=dict)
    admin_name: str = Field(min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=6)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    plan: str | None = Field(default=None, max_length=50)
    status: Literal["active", "disabled"] | None = None
    settings: dict | None = None


class OrganizationUserCreate(AdminUserCreate):
    role: Literal["doctor", "pharmacist", "admin", "auditor"] = "doctor"


class AdminOverview(BaseModel):
    organization_id: str
    users_total: int
    active_users: int
    patients_total: int
    cases_total: int
    ai_responses_total: int
    portal_accounts_total: int
    portal_uploads_total: int
    portal_uploads_requiring_review: int
    audit_events_total: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class PatientPortalUserRead(BaseModel):
    id: str
    name: str
    medical_record_no: str
    organization_id: str


class PatientPortalLoginRequest(BaseModel):
    login_identifier: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=1)


class PatientPortalLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    patient: PatientPortalUserRead


class PatientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    medical_record_no: str = Field(min_length=2, max_length=100)
    date_of_birth: date
    age: int = Field(ge=0, le=130)
    gender: Gender
    phone: str | None = None
    last_visit: date | None = None


class PatientRead(PatientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class SymptomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    severity: Literal["mild", "moderate", "severe"]
    onset_date: date | None = None
    duration: str | None = None
    note: str | None = None


class SymptomRead(SymptomCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str


class VitalSignCreate(BaseModel):
    type: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=50)
    measured_at: datetime | None = None


class VitalSignRead(VitalSignCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str


class LabResultCreate(BaseModel):
    test_name: str = Field(min_length=1, max_length=255)
    value: float
    unit: str = Field(min_length=1, max_length=50)
    reference_low: float | None = None
    reference_high: float | None = None
    abnormal_flag: bool | None = None
    collected_at: date

    @model_validator(mode="after")
    def infer_abnormal_flag(self) -> "LabResultCreate":
        if self.abnormal_flag is None and self.reference_low is not None and self.reference_high is not None:
            self.abnormal_flag = self.value < self.reference_low or self.value > self.reference_high
        elif self.abnormal_flag is None:
            self.abnormal_flag = False
        return self


class LabResultRead(LabResultCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    abnormal_flag: bool


class MedicationIngredientCreate(BaseModel):
    ingredient_name: str = Field(min_length=1, max_length=255)
    strength: str | None = None
    unit: str | None = None


class MedicationIngredientRead(MedicationIngredientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str


class MedicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    dose: str = Field(min_length=1, max_length=100)
    route: str = Field(min_length=1, max_length=100)
    frequency: str = Field(min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    status: Literal["active", "stopped"] = "active"
    ingredients: list[MedicationIngredientCreate] = Field(default_factory=list)


class MedicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    dose: str
    route: str
    frequency: str
    start_date: date | None
    end_date: date | None
    status: str
    ingredients: list[MedicationIngredientRead]


class SupplementCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    ingredients: list[str] = Field(default_factory=list)
    dose: str | None = None
    start_date: date | None = None


class SupplementRead(SupplementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str


class AllergyCreate(BaseModel):
    substance: str = Field(min_length=1, max_length=255)
    reaction: str | None = None
    severity: Severity = "unknown"
    verified_status: Literal["unverified", "patient_reported", "doctor_verified"] = "unverified"


class AllergyRead(AllergyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str


class PatientVerifiedFactCreate(BaseModel):
    fact_type: Literal["allergy", "medication_history", "past_history", "social_history", "baseline_lab", "other"]
    fact_value: str = Field(min_length=1)
    source_case_id: str | None = None


class PatientVerifiedFactRead(PatientVerifiedFactCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    patient_id: str
    verified_by: str
    verified_at: datetime


class ClinicalCaseCreate(BaseModel):
    patient_id: str
    chief_complaint: str = Field(min_length=3)
    notes: str | None = None


class ClinicalCaseUpdate(BaseModel):
    chief_complaint: str | None = Field(default=None, min_length=3)
    notes: str | None = None
    status: CaseStatus | None = None
    has_red_flag: bool | None = None


class PatientLabBatchCreate(BaseModel):
    case_id: str | None = None
    labs: list[LabResultCreate] = Field(min_length=1)
    chief_complaint: str = "Patient-level lab entry"


class ClinicalCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    encounter_id: str
    patient_id: str
    created_by: str
    chief_complaint: str
    status: CaseStatus | str
    has_red_flag: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    symptoms: list[SymptomRead] = Field(default_factory=list)
    vital_signs: list[VitalSignRead] = Field(default_factory=list)
    lab_results: list[LabResultRead] = Field(default_factory=list)
    medications: list[MedicationRead] = Field(default_factory=list)
    supplements: list[SupplementRead] = Field(default_factory=list)
    attachments: list["CaseAttachmentRead"] = Field(default_factory=list)


class RecommendedTest(BaseModel):
    name: str
    reason: str
    priority: Literal["urgent", "routine"]


class DiagnosisSuggestion(BaseModel):
    name: str
    confidence: int = Field(ge=0, le=100)
    supporting_evidence: list[str]
    missing_evidence: list[str]
    icd_code: str | None = None


class MedicationWarning(BaseModel):
    type: Literal["interaction", "duplicate_ingredient", "allergy", "contraindication", "dose_risk"]
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    medications: list[str]


class SourceCitation(BaseModel):
    title: str
    source: str
    version: str
    url: str | None = None


class CausalityAssessment(BaseModel):
    type: Literal["disease_related", "medication_related", "unclear"]
    confidence: int = Field(ge=0, le=100)
    evidence: str


class AIContent(BaseModel):
    clinical_summary: str
    differential_diagnosis: list[DiagnosisSuggestion]
    missing_information: list[str]
    recommended_tests: list[RecommendedTest]
    medication_warnings: list[MedicationWarning]
    causality_assessment: CausalityAssessment
    red_flags: list[str]
    citations: list[SourceCitation]
    confidence_level: int = Field(ge=0, le=100)
    doctor_confirmation_required: bool = True


class AIResponseRead(BaseModel):
    id: str
    case_id: str
    request_id: str
    response_type: str
    content: AIContent
    confidence: int
    safety_status: str
    model_version: str
    generated_at: datetime


class CaseAttachmentCreate(BaseModel):
    section: Literal["basic", "symptoms", "vitals", "labs", "medications", "allergies", "knowledge"] = "labs"
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=100)
    data_url: str = Field(min_length=20)

    @model_validator(mode="after")
    def require_supported_data_url(self) -> "CaseAttachmentCreate":
        if not self.data_url.startswith("data:"):
            raise ValueError("data_url must be a data URL")
        if self.content_type not in {"image/png", "image/jpeg", "image/jpg", "image/webp", "application/pdf", "text/plain"}:
            raise ValueError("Unsupported attachment content_type")
        return self


class CaseAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    patient_id: str
    section: str
    file_name: str
    content_type: str
    sha256: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    extraction_status: str
    created_at: datetime


class DocumentExtractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    attachment_id: str
    model: str
    status: str
    raw_text: str | None = None
    result_json: dict
    notes: list[str]
    created_at: datetime


class ProposedClinicalFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    patient_id: str
    attachment_id: str | None = None
    extraction_id: str | None = None
    fact_type: str
    fact_json: dict
    source_text: str | None = None
    confidence: int
    status: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    created_at: datetime


class ProposedFactReview(BaseModel):
    note: str | None = None
    fact_json: dict | None = None


class PatientExplanationContent(BaseModel):
    summary: str
    lab_meaning: str
    plain_language: list[str]
    next_questions: list[str]
    safety_notes: list[str]
    disclaimer: str


class ExtractedLabObservation(BaseModel):
    test_name: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    abnormal_flag: bool | None = None
    source: str
    confidence: int = Field(ge=0, le=100)


class ImageExtractionResult(BaseModel):
    status: Literal["not_requested", "processed", "requires_review", "failed"]
    model: str
    image_sha256: str | None = None
    image_content_type: str | None = None
    image_size_bytes: int | None = None
    image_width: int | None = None
    image_height: int | None = None
    ocr_engine: str | None = None
    ocr_languages: str | None = None
    ocr_text: str | None = None
    observations: list[ExtractedLabObservation] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PatientExplanationCreate(BaseModel):
    diagnosis_text: str | None = Field(default=None, max_length=4000)
    lab_name: str | None = Field(default=None, max_length=255)
    lab_value: str | None = Field(default=None, max_length=100)
    lab_unit: str | None = Field(default=None, max_length=50)
    reference_range: str | None = Field(default=None, max_length=100)
    lab_collected_at: date | None = None
    attachment_name: str | None = Field(default=None, max_length=255)
    attachment_content_type: str | None = Field(default=None, max_length=100)
    attachment_data_url: str | None = None
    patient_question: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def require_clinical_input(self) -> "PatientExplanationCreate":
        has_stored_attachment = bool(getattr(self, "has_attachment", False))
        if not any([self.diagnosis_text, self.lab_name, self.patient_question, self.attachment_data_url, has_stored_attachment]):
            raise ValueError("diagnosis_text, lab_name, or patient_question is required")
        if self.attachment_data_url and not self.attachment_data_url.startswith("data:image/"):
            raise ValueError("attachment_data_url must be an image data URL")
        return self


class PatientExplanationRead(PatientExplanationCreate):
    id: str
    patient_id: str
    attachment_data_url: str | None = None
    attachment_object_key: str | None = None
    attachment_sha256: str | None = None
    attachment_size_bytes: int | None = None
    attachment_width: int | None = None
    attachment_height: int | None = None
    has_attachment: bool = False
    extracted_lab_data: ImageExtractionResult
    extraction_status: str
    extraction_model: str | None
    content: PatientExplanationContent
    safety_status: str
    created_at: datetime


class AdminPortalExplanationRead(PatientExplanationRead):
    patient_name: str
    patient_medical_record_no: str


class AdminPortalExplanationUpdate(BaseModel):
    extraction_status: Literal["not_requested", "processed", "requires_review", "failed"] | None = None
    safety_status: str | None = Field(default=None, max_length=50)


class DoctorDecisionCreate(BaseModel):
    ai_response_id: str
    decision: DecisionValue
    final_note: str | None = None


class DoctorDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ai_response_id: str
    doctor_id: str
    decision: str
    final_note: str | None
    created_at: datetime


class FeedbackCreate(BaseModel):
    action: DecisionValue
    reason_code: str | None = None
    correction_text: str | None = None
    usefulness_score: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def reject_requires_reason(self) -> "FeedbackCreate":
        if self.action == "reject" and not self.reason_code:
            raise ValueError("reason_code is required when rejecting an AI response")
        return self


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    metadata_json: dict
    created_at: datetime


ClinicalCaseRead.model_rebuild()
