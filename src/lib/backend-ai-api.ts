import 'server-only'

import type { AIResponse, CaseAttachment, ClinicalCase, LabResult, Medication, Patient, Symptom } from '@/types'

type BackendPatient = {
  id: string
  medical_record_no: string
}

type BackendCase = {
  id: string
}

type BackendAIResponse = {
  id: string
  response_type: string
  content: {
    clinical_summary: string
    differential_diagnosis: Array<{
      name: string
      confidence: number
      supporting_evidence: string[]
      missing_evidence: string[]
      icd_code?: string | null
    }>
    missing_information: string[]
    recommended_tests: Array<{
      name: string
      reason: string
      priority: 'urgent' | 'routine'
    }>
    medication_warnings: Array<{
      type: AIResponse['medicationWarnings'][number]['type']
      severity: AIResponse['medicationWarnings'][number]['severity']
      description: string
      medications: string[]
    }>
    causality_assessment: {
      type: AIResponse['causalityAssessment']['type']
      confidence: number
      evidence: string
    }
    red_flags: string[]
    citations: Array<{
      title: string
      source: string
      version: string
      url?: string | null
    }>
    confidence_level: number
    doctor_confirmation_required: boolean
  }
}

type RuntimeCase = ClinicalCase & {
  clinicalNote?: string
  allergies?: Array<{
    substance?: string
    reaction?: string
    severity?: 'mild' | 'moderate' | 'severe' | 'unknown'
  }>
}

const BACKEND_BASE_URL = process.env.MEDCORE_BACKEND_URL ?? 'http://localhost:8000'

function backendUrl(path: string) {
  return `${BACKEND_BASE_URL.replace(/\/$/, '')}${path}`
}

async function backendRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(backendUrl(path), {
    ...init,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...init.headers,
    },
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json() as { detail?: string; error?: string; message?: string }
      detail = body.detail || body.error || body.message || detail
    } catch {
      // Keep the HTTP status text.
    }
    throw new Error(`Backend AI API алдаа: ${detail} (HTTP ${response.status})`)
  }

  return response.json() as Promise<T>
}

async function backendJson<T>(token: string, path: string, method: string, payload?: unknown): Promise<T> {
  return backendRequest<T>(path, {
    method,
    headers: { Authorization: `Bearer ${token}` },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  })
}

function patientPayload(patient: Patient) {
  return {
    name: patient.name,
    medical_record_no: patient.medicalRecordNo,
    date_of_birth: patient.dateOfBirth,
    age: patient.age,
    gender: patient.gender,
    phone: patient.phone ?? null,
    last_visit: patient.lastVisit ?? null,
  }
}

async function ensureBackendPatient(token: string, patient: Patient) {
  const matches = await backendJson<BackendPatient[]>(token, `/patients?q=${encodeURIComponent(patient.medicalRecordNo)}&limit=10`, 'GET')
  const existing = matches.find((item) => item.medical_record_no === patient.medicalRecordNo)
  if (existing) return existing

  return backendJson<BackendPatient>(token, '/patients', 'POST', patientPayload(patient))
}

async function createBackendCase(token: string, clinicalCase: RuntimeCase, patient: BackendPatient) {
  return backendJson<BackendCase>(token, '/cases', 'POST', {
    patient_id: patient.id,
    chief_complaint: clinicalCase.chiefComplaint,
    notes: clinicalCase.clinicalNote ?? null,
  })
}

function symptomPayload(symptom: Symptom) {
  return {
    name: symptom.name,
    severity: symptom.severity,
    onset_date: symptom.onsetDate || null,
    duration: symptom.duration || null,
    note: symptom.note ?? null,
  }
}

function labPayload(lab: LabResult) {
  return {
    test_name: lab.testName,
    value: lab.value,
    unit: lab.unit || 'unknown',
    reference_low: lab.referenceRangeLow,
    reference_high: lab.referenceRangeHigh,
    abnormal_flag: lab.abnormalFlag,
    collected_at: lab.collectedAt,
  }
}

function medicationPayload(medication: Medication) {
  return {
    name: medication.name,
    dose: medication.dose || 'unknown',
    route: medication.route || 'unknown',
    frequency: medication.frequency || 'unknown',
    start_date: medication.startDate || null,
    status: medication.status,
    ingredients: medication.ingredients.map((ingredient) => ({ ingredient_name: ingredient })),
  }
}

function attachmentPayload(attachment: CaseAttachment) {
  return {
    section: attachment.section,
    file_name: attachment.fileName,
    content_type: attachment.contentType,
    data_url: attachment.dataUrl,
  }
}

async function syncStructuredCaseData(token: string, backendCase: BackendCase, clinicalCase: RuntimeCase, backendPatient: BackendPatient) {
  for (const symptom of clinicalCase.symptoms) {
    await backendJson(token, `/cases/${backendCase.id}/symptoms`, 'POST', symptomPayload(symptom))
  }

  for (const lab of clinicalCase.labResults) {
    if (!lab.collectedAt) continue
    await backendJson(token, `/cases/${backendCase.id}/labs`, 'POST', labPayload(lab))
  }

  for (const medication of clinicalCase.medications) {
    await backendJson(token, `/cases/${backendCase.id}/medications`, 'POST', medicationPayload(medication))
  }

  for (const allergy of clinicalCase.allergies ?? []) {
    if (!allergy.substance?.trim()) continue
    await backendJson(token, `/patients/${backendPatient.id}/allergies`, 'POST', {
      substance: allergy.substance,
      reaction: allergy.reaction || null,
      severity: allergy.severity ?? 'unknown',
      verified_status: 'doctor_verified',
    })
  }

  for (const attachment of clinicalCase.attachments ?? []) {
    await backendJson(token, `/cases/${backendCase.id}/attachments`, 'POST', attachmentPayload(attachment))
  }
}

function mapBackendAIResponse(response: BackendAIResponse): AIResponse {
  const content = response.content
  return {
    id: response.id,
    clinicalSummary: content.clinical_summary,
    differentialDiagnosis: content.differential_diagnosis.map((item) => ({
      name: item.name,
      confidence: item.confidence,
      supportingEvidence: item.supporting_evidence,
      missingEvidence: item.missing_evidence,
      icdCode: item.icd_code ?? undefined,
    })),
    missingInformation: content.missing_information,
    recommendedTests: content.recommended_tests,
    medicationWarnings: content.medication_warnings,
    causalityAssessment: content.causality_assessment,
    redFlags: content.red_flags,
    citations: content.citations.map((citation) => ({
      title: citation.title,
      source: citation.source,
      version: citation.version,
      url: citation.url ?? undefined,
    })),
    confidenceLevel: content.confidence_level,
    doctorConfirmationRequired: content.doctor_confirmation_required,
  }
}

export async function runBackendAIAnalysis(clinicalCase: ClinicalCase, patient: Patient, token: string): Promise<AIResponse> {
  const backendPatient = await ensureBackendPatient(token, patient)
  const backendCase = await createBackendCase(token, clinicalCase, backendPatient)
  await syncStructuredCaseData(token, backendCase, clinicalCase, backendPatient)
  const response = await backendJson<BackendAIResponse>(token, `/cases/${backendCase.id}/ai/differential-diagnosis`, 'POST', {})
  return mapBackendAIResponse(response)
}
