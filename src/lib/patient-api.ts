export type PatientPortalUser = {
  id: string
  name: string
  medical_record_no: string
  organization_id: string
}

export type PatientExplanationContent = {
  summary: string
  lab_meaning: string
  plain_language: string[]
  next_questions: string[]
  safety_notes: string[]
  disclaimer: string
}

export type ExtractedLabObservation = {
  test_name: string
  value: string | null
  unit: string | null
  reference_range: string | null
  abnormal_flag: boolean | null
  source: string
  confidence: number
}

export type ImageExtractionResult = {
  status: 'not_requested' | 'processed' | 'requires_review' | 'failed'
  model: string
  image_sha256: string | null
  image_content_type: string | null
  image_size_bytes: number | null
  image_width: number | null
  image_height: number | null
  ocr_engine: string | null
  ocr_languages: string | null
  ocr_text: string | null
  observations: ExtractedLabObservation[]
  notes: string[]
}

export type PatientExplanation = {
  id: string
  patient_id: string
  diagnosis_text: string | null
  lab_name: string | null
  lab_value: string | null
  lab_unit: string | null
  reference_range: string | null
  lab_collected_at: string | null
  attachment_name: string | null
  attachment_content_type: string | null
  attachment_data_url: string | null
  attachment_object_key: string | null
  attachment_sha256: string | null
  attachment_size_bytes: number | null
  attachment_width: number | null
  attachment_height: number | null
  has_attachment: boolean
  extracted_lab_data: ImageExtractionResult
  extraction_status: string
  extraction_model: string | null
  patient_question: string | null
  content: PatientExplanationContent
  safety_status: string
  created_at: string
}

export type PatientExplanationPayload = {
  diagnosis_text: string | null
  lab_name: string | null
  lab_value: string | null
  lab_unit: string | null
  reference_range: string | null
  lab_collected_at: string | null
  attachment_name: string | null
  attachment_content_type: string | null
  attachment_data_url: string | null
  patient_question: string | null
}

export const PATIENT_TOKEN_KEY = 'medcore.patientPortal.token'
export const PATIENT_PROFILE_KEY = 'medcore.patientPortal.profile'

// Default: ижил Next.js серверийн дотоод API route-ууд (/api/patient-portal/...).
// Тусдаа backend ашиглах бол NEXT_PUBLIC_API_BASE_URL-ийг тохируулна.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api'

export async function patientLogin(login_identifier: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/patient-portal/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login_identifier, password }),
  })
  if (!response.ok) throw new Error('Өвчтөний нэвтрэх мэдээлэл буруу байна')
  return response.json() as Promise<{ access_token: string; token_type: string; patient: PatientPortalUser }>
}

export async function fetchPatientExplanations(token: string) {
  const response = await fetch(`${API_BASE_URL}/patient-portal/explanations`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error('Өмнөх тайлбаруудыг татаж чадсангүй')
  return response.json() as Promise<PatientExplanation[]>
}

export async function createPatientExplanation(token: string, payload: PatientExplanationPayload) {
  const response = await fetch(`${API_BASE_URL}/patient-portal/explanations`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error('Тайлбарыг database-д хадгалж чадсангүй')
  return response.json() as Promise<PatientExplanation>
}

export async function fetchPatientExplanationImage(token: string, explanationId: string) {
  const response = await fetch(`${API_BASE_URL}/patient-portal/explanations/${explanationId}/image`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error('Зургийг татаж чадсангүй')
  return response.blob()
}
