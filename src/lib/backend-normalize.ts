import type { ClinicalCase, LabResult, Medication, Patient, Symptom } from '@/types'

type BackendPatient = {
  id: string
  name: string
  age: number
  gender: Patient['gender']
  medical_record_no: string
  date_of_birth: string
  phone?: string | null
  last_visit?: string | null
}

type BackendCase = {
  id: string
  patient_id: string
  patient?: { name?: string } | null
  chief_complaint: string
  status: ClinicalCase['status']
  created_at: string
  updated_at: string
  has_red_flag: boolean
  symptoms?: Array<{
    id: string
    name: string
    severity: Symptom['severity']
    onset_date?: string | null
    duration?: string | null
    note?: string | null
  }>
  lab_results?: Array<{
    id: string
    test_name: string
    value: number
    unit: string
    reference_low?: number | null
    reference_high?: number | null
    abnormal_flag: boolean
    collected_at: string
  }>
  medications?: Array<{
    id: string
    name: string
    dose: string
    route: string
    frequency: string
    start_date?: string | null
    status: Medication['status']
    ingredients?: Array<{ ingredient_name: string } | string>
  }>
}

export function normalizePatient(patient: BackendPatient): Patient {
  return {
    id: patient.id,
    name: patient.name,
    age: patient.age,
    gender: patient.gender,
    medicalRecordNo: patient.medical_record_no,
    dateOfBirth: patient.date_of_birth,
    phone: patient.phone ?? undefined,
    lastVisit: patient.last_visit ?? undefined,
  }
}

export function normalizeCase(clinicalCase: BackendCase): ClinicalCase {
  return {
    id: clinicalCase.id,
    patientId: clinicalCase.patient_id,
    patientName: clinicalCase.patient?.name ?? '',
    chiefComplaint: clinicalCase.chief_complaint,
    status: clinicalCase.status,
    createdAt: clinicalCase.created_at,
    updatedAt: clinicalCase.updated_at,
    hasRedFlag: clinicalCase.has_red_flag,
    symptoms: (clinicalCase.symptoms ?? []).map((symptom) => ({
      id: symptom.id,
      name: symptom.name,
      severity: symptom.severity,
      onsetDate: symptom.onset_date ?? '',
      duration: symptom.duration ?? '',
      note: symptom.note ?? undefined,
    })),
    labResults: (clinicalCase.lab_results ?? []).map(normalizeLab),
    medications: (clinicalCase.medications ?? []).map((medication) => ({
      id: medication.id,
      name: medication.name,
      dose: medication.dose,
      route: medication.route,
      frequency: medication.frequency,
      startDate: medication.start_date ?? '',
      ingredients: (medication.ingredients ?? []).map((ingredient) =>
        typeof ingredient === 'string' ? ingredient : ingredient.ingredient_name
      ),
      status: medication.status,
    })),
    attachments: [],
  }
}

function normalizeLab(lab: NonNullable<BackendCase['lab_results']>[number]): LabResult {
  return {
    id: lab.id,
    testName: lab.test_name,
    value: lab.value,
    unit: lab.unit,
    referenceRangeLow: lab.reference_low ?? 0,
    referenceRangeHigh: lab.reference_high ?? 0,
    abnormalFlag: lab.abnormal_flag,
    collectedAt: lab.collected_at,
  }
}

export function toBackendPatientCreate(input: {
  name?: string
  dateOfBirth?: string
  dob?: string
  gender?: Patient['gender']
  phone?: string
  medicalRecordNo?: string
}) {
  const dateOfBirth = input.dateOfBirth || input.dob || ''
  const birth = new Date(dateOfBirth)
  let age = 0
  if (!Number.isNaN(birth.getTime())) {
    const now = new Date()
    age = now.getFullYear() - birth.getFullYear()
    const monthDelta = now.getMonth() - birth.getMonth()
    if (monthDelta < 0 || (monthDelta === 0 && now.getDate() < birth.getDate())) age -= 1
  }
  return {
    name: input.name,
    medical_record_no: input.medicalRecordNo,
    date_of_birth: dateOfBirth,
    age,
    gender: input.gender ?? 'other',
    phone: input.phone,
  }
}

export function toBackendCaseCreate(input: { patientId?: string; chiefComplaint?: string; notes?: string }) {
  return {
    patient_id: input.patientId,
    chief_complaint: input.chiefComplaint,
    notes: input.notes,
  }
}

export function toBackendCaseUpdate(input: {
  chiefComplaint?: string
  notes?: string | null
  status?: ClinicalCase['status']
  hasRedFlag?: boolean
}) {
  return {
    chief_complaint: input.chiefComplaint,
    notes: input.notes,
    status: input.status,
    has_red_flag: input.hasRedFlag,
  }
}

export function toBackendLab(lab: Partial<LabResult>) {
  return {
    test_name: lab.testName,
    value: lab.value,
    unit: lab.unit,
    reference_low: lab.referenceRangeLow,
    reference_high: lab.referenceRangeHigh,
    abnormal_flag: lab.abnormalFlag,
    collected_at: lab.collectedAt,
  }
}
