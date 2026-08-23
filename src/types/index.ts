export type UserRole = 'doctor' | 'pharmacist' | 'admin' | 'auditor' | 'super_admin'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  organization: string
  avatar?: string
}

export interface Patient {
  id: string
  name: string
  age: number
  gender: 'male' | 'female' | 'other'
  medicalRecordNo: string
  dateOfBirth: string
  phone?: string
  lastVisit?: string
}

export interface Symptom {
  id: string
  name: string
  severity: 'mild' | 'moderate' | 'severe'
  onsetDate: string
  duration: string
  note?: string
}

export interface LabResult {
  id: string
  testName: string
  value: number
  unit: string
  referenceRangeLow: number
  referenceRangeHigh: number
  abnormalFlag: boolean
  collectedAt: string
  dateReviewRequired?: boolean
}

export interface PatientLabResult extends LabResult {
  patientId: string
  caseId?: string
  source: 'manual' | 'image_ocr'
  sourceAttachmentId?: string
  createdAt: string
}

export interface Medication {
  id: string
  name: string
  dose: string
  route: string
  frequency: string
  startDate: string
  ingredients: string[]
  status: 'active' | 'stopped'
}

export type CaseAttachmentSection = 'basic' | 'symptoms' | 'vitals' | 'labs' | 'medications' | 'allergies'

export interface CaseAttachment {
  id: string
  section: CaseAttachmentSection
  fileName: string
  contentType: string
  sizeBytes: number
  dataUrl: string
  createdAt: string
}

export interface DiagnosisSuggestion {
  name: string
  confidence: number
  supportingEvidence: string[]
  missingEvidence: string[]
  icdCode?: string
}

export interface MedicationWarning {
  type: 'interaction' | 'duplicate_ingredient' | 'allergy' | 'contraindication' | 'dose_risk'
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  medications: string[]
}

export interface SourceCitation {
  title: string
  source: string
  version: string
  url?: string
}

export interface AIResponse {
  id: string
  clinicalSummary: string
  differentialDiagnosis: DiagnosisSuggestion[]
  missingInformation: string[]
  recommendedTests: { name: string; reason: string; priority: 'urgent' | 'routine' }[]
  medicationWarnings: MedicationWarning[]
  causalityAssessment: {
    type: 'disease_related' | 'medication_related' | 'unclear'
    confidence: number
    evidence: string
  }
  redFlags: string[]
  citations: SourceCitation[]
  confidenceLevel: number
  doctorConfirmationRequired: boolean
}

export interface ClinicalCase {
  id: string
  patientId: string
  patientName: string
  chiefComplaint: string
  status: 'draft' | 'ai_pending' | 'ai_complete' | 'doctor_reviewed' | 'finalized'
  createdAt: string
  updatedAt: string
  hasRedFlag: boolean
  symptoms: Symptom[]
  labResults: LabResult[]
  medications: Medication[]
  attachments?: CaseAttachment[]
  aiResponse?: AIResponse
}
