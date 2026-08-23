from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - optional dependency in sqlite-only dev shells
    Vector = None


JsonType = JSON().with_variant(JSONB, "postgresql")
EMBEDDING_DIMENSIONS = 768  # intfloat/multilingual-e5-base output size
EmbeddingType = Vector(EMBEDDING_DIMENSIONS).with_variant(JSON(), "sqlite") if Vector else JsonType


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="mvp", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    settings: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    patients: Mapped[list["Patient"]] = relationship(back_populates="organization")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_users_org_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Organization] = relationship(back_populates="users")


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("organization_id", "medical_record_no", name="uq_patients_org_mrn"),
        Index("ix_patients_org_name", "organization_id", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    medical_record_no: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    last_visit: Mapped[date | None] = mapped_column(Date)

    organization: Mapped[Organization] = relationship(back_populates="patients")
    encounters: Mapped[list["Encounter"]] = relationship(back_populates="patient")
    allergies: Mapped[list["Allergy"]] = relationship(back_populates="patient")
    verified_facts: Mapped[list["PatientVerifiedFact"]] = relationship(back_populates="patient")
    portal_account: Mapped["PatientPortalAccount | None"] = relationship(back_populates="patient")
    portal_explanations: Mapped[list["PatientPortalExplanation"]] = relationship(back_populates="patient")


class PatientPortalAccount(Base, TimestampMixin):
    __tablename__ = "patient_portal_accounts"
    __table_args__ = (UniqueConstraint("organization_id", "login_identifier", name="uq_patient_portal_org_login"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), unique=True, index=True, nullable=False)
    login_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped[Patient] = relationship(back_populates="portal_account")


class PatientPortalExplanation(Base):
    __tablename__ = "patient_portal_explanations"
    __table_args__ = (
        Index("ix_patient_portal_patient_created", "patient_id", "created_at"),
        Index("ix_patient_portal_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    diagnosis_text: Mapped[str | None] = mapped_column(Text)
    lab_name: Mapped[str | None] = mapped_column(String(255))
    lab_value: Mapped[str | None] = mapped_column(String(100))
    lab_unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100))
    lab_collected_at: Mapped[date | None] = mapped_column(Date)
    attachment_name: Mapped[str | None] = mapped_column(String(255))
    attachment_content_type: Mapped[str | None] = mapped_column(String(100))
    attachment_object_key: Mapped[str | None] = mapped_column(String(500))
    attachment_sha256: Mapped[str | None] = mapped_column(String(64))
    attachment_size_bytes: Mapped[int | None] = mapped_column(Integer)
    attachment_width: Mapped[int | None] = mapped_column(Integer)
    attachment_height: Mapped[int | None] = mapped_column(Integer)
    attachment_data_url: Mapped[str | None] = mapped_column(Text)
    extracted_lab_data: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(50), default="not_requested", nullable=False)
    extraction_model: Mapped[str | None] = mapped_column(String(100))
    patient_question: Mapped[str | None] = mapped_column(Text)
    explanation_json: Mapped[dict] = mapped_column(JsonType, nullable=False)
    safety_status: Mapped[str] = mapped_column(String(50), default="patient_education_only", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="portal_explanations")


class Encounter(Base, TimestampMixin):
    __tablename__ = "encounters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    encounter_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="encounters")
    cases: Mapped[list["ClinicalCase"]] = relationship(back_populates="encounter")


class ClinicalCase(Base, TimestampMixin):
    __tablename__ = "clinical_cases"
    __table_args__ = (Index("ix_cases_org_status", "organization_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    has_red_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    encounter: Mapped[Encounter] = relationship(back_populates="cases")
    patient: Mapped[Patient] = relationship()
    symptoms: Mapped[list["Symptom"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    vital_signs: Mapped[list["VitalSign"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    lab_results: Mapped[list["LabResult"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    medications: Mapped[list["Medication"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    supplements: Mapped[list["Supplement"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    ai_responses: Mapped[list["AIResponse"]] = relationship(back_populates="case")
    attachments: Mapped[list["CaseAttachment"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    proposed_facts: Mapped[list["ProposedClinicalFact"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Symptom(Base):
    __tablename__ = "symptoms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    onset_date: Mapped[date | None] = mapped_column(Date)
    duration: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text)

    case: Mapped[ClinicalCase] = relationship(back_populates="symptoms")


class VitalSign(Base):
    __tablename__ = "vital_signs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case: Mapped[ClinicalCase] = relationship(back_populates="vital_signs")


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_low: Mapped[float | None] = mapped_column(Float)
    reference_high: Mapped[float | None] = mapped_column(Float)
    abnormal_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    collected_at: Mapped[date] = mapped_column(Date, nullable=False)

    case: Mapped[ClinicalCase] = relationship(back_populates="lab_results")


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("source_hash", name="uq_knowledge_documents_source_hash"),
        Index("ix_knowledge_documents_category", "category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="clinical", nullable=False)
    version: Mapped[str] = mapped_column(String(80), default="local", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base, TimestampMixin):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_knowledge_chunks_document", "document_id"),
        Index("ix_knowledge_chunks_category", "category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType)
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(80), default="clinical", nullable=False)
    source_title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class CaseAttachment(Base, TimestampMixin):
    __tablename__ = "case_attachments"
    __table_args__ = (Index("ix_case_attachments_case_section", "case_id", "section"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    section: Mapped[str] = mapped_column(String(80), default="labs", nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    extraction_status: Mapped[str] = mapped_column(String(50), default="not_requested", nullable=False)

    case: Mapped[ClinicalCase] = relationship(back_populates="attachments")
    extractions: Mapped[list["DocumentExtraction"]] = relationship(back_populates="attachment", cascade="all, delete-orphan")


class DocumentExtraction(Base, TimestampMixin):
    __tablename__ = "document_extractions"
    __table_args__ = (Index("ix_document_extractions_attachment", "attachment_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    attachment_id: Mapped[str] = mapped_column(ForeignKey("case_attachments.id"), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="requires_review", nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    notes: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)

    attachment: Mapped[CaseAttachment] = relationship(back_populates="extractions")


class ProposedClinicalFact(Base, TimestampMixin):
    __tablename__ = "proposed_clinical_facts"
    __table_args__ = (
        Index("ix_proposed_facts_case_status", "case_id", "status"),
        Index("ix_proposed_facts_patient", "patient_id", "fact_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    attachment_id: Mapped[str | None] = mapped_column(ForeignKey("case_attachments.id"), index=True)
    extraction_id: Mapped[str | None] = mapped_column(ForeignKey("document_extractions.id"), index=True)
    fact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_json: Mapped[dict] = mapped_column(JsonType, nullable=False)
    source_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_review", nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)

    case: Mapped[ClinicalCase] = relationship(back_populates="proposed_facts")


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dose: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)

    case: Mapped[ClinicalCase] = relationship(back_populates="medications")
    ingredients: Mapped[list["MedicationIngredient"]] = relationship(back_populates="medication", cascade="all, delete-orphan")


class MedicationIngredient(Base):
    __tablename__ = "medication_ingredients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    medication_id: Mapped[str] = mapped_column(ForeignKey("medications.id"), index=True, nullable=False)
    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str | None] = mapped_column(String(50))

    medication: Mapped[Medication] = relationship(back_populates="ingredients")


class Supplement(Base):
    __tablename__ = "supplements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ingredients: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    dose: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)

    case: Mapped[ClinicalCase] = relationship(back_populates="supplements")


class Allergy(Base):
    __tablename__ = "allergies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    substance: Mapped[str] = mapped_column(String(255), nullable=False)
    reaction: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    verified_status: Mapped[str] = mapped_column(String(30), default="unverified", nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="allergies")


class AIRequest(Base):
    __tablename__ = "ai_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    request_type: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="rule-based-mvp", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), default="medcore-mvp-v1", nullable=False)
    token_usage: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AIResponse(Base):
    __tablename__ = "ai_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True, nullable=False)
    request_id: Mapped[str] = mapped_column(ForeignKey("ai_requests.id"), index=True, nullable=False)
    response_type: Mapped[str] = mapped_column(String(80), nullable=False)
    content_json: Mapped[dict] = mapped_column(JsonType, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_status: Mapped[str] = mapped_column(String(50), default="doctor_confirmation_required", nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), default="rule-based-mvp-v1", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case: Mapped[ClinicalCase] = relationship(back_populates="ai_responses")


class DoctorDecision(Base):
    __tablename__ = "doctor_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    ai_response_id: Mapped[str] = mapped_column(ForeignKey("ai_responses.id"), index=True, nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    final_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DoctorFeedbackEvent(Base):
    __tablename__ = "doctor_feedback_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    ai_response_id: Mapped[str] = mapped_column(ForeignKey("ai_responses.id"), index=True, nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(80))
    correction_text: Mapped[str | None] = mapped_column(Text)
    usefulness_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class PatientVerifiedFact(Base):
    __tablename__ = "patient_verified_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    fact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_value: Mapped[str] = mapped_column(Text, nullable=False)
    verified_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_case_id: Mapped[str | None] = mapped_column(ForeignKey("clinical_cases.id"))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="verified_facts")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    before_hash: Mapped[str | None] = mapped_column(String(128))
    after_hash: Mapped[str | None] = mapped_column(String(128))
    ip_address: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
