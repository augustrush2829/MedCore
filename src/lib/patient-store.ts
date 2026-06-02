import 'server-only'
import { listPatients } from './clinical-store'

// Fallback in-memory store. Production-д FastAPI/PostgreSQL + JWT ашиглана.

export interface LabObservation {
  test_name: string
  value: string | null
  unit: string | null
  reference_range: string | null
  abnormal_flag: boolean | null
  source: string
  confidence: number
}

export interface ExtractionResult {
  status: 'not_requested' | 'processed' | 'requires_review' | 'failed'
  model: string
  observations: LabObservation[]
  notes: string[]
  ocr_text: string | null
}

export interface StoredExplanation {
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
  patient_question: string | null
  content: {
    summary: string
    lab_meaning: string
    plain_language: string[]
    next_questions: string[]
    safety_notes: string[]
    disclaimer: string
  }
  extracted: ExtractionResult
  safety_status: string
  created_at: string
}

const explanations: StoredExplanation[] = []
const PATIENT_PASSWORD = process.env.PATIENT_DEMO_PASSWORD

export interface PatientPortalUser {
  id: string
  name: string
  medical_record_no: string
  organization_id: string
}

export function authenticate(loginIdentifier: string, password: string): PatientPortalUser | null {
  if (!PATIENT_PASSWORD || process.env.MEDCORE_DEMO_DATA !== 'true') return null
  if (password !== PATIENT_PASSWORD) return null
  const p = listPatients().find(
    (x) => x.medicalRecordNo.toLowerCase() === loginIdentifier.trim().toLowerCase()
  )
  if (!p) return null
  return { id: p.id, name: p.name, medical_record_no: p.medicalRecordNo, organization_id: 'org-1' }
}

// Fallback token: base64(patient_id). Production-д backend JWT ашиглана.
export function makeToken(patientId: string): string {
  return Buffer.from(`patient:${patientId}`).toString('base64')
}

export function verifyToken(authHeader: string | null): string | null {
  if (!authHeader?.startsWith('Bearer ')) return null
  try {
    const decoded = Buffer.from(authHeader.slice(7), 'base64').toString('utf-8')
    const [prefix, patientId] = decoded.split(':')
    return prefix === 'patient' && patientId ? patientId : null
  } catch {
    return null
  }
}

// Lab утгыг хэвийн хязгаартай харьцуулж энгийн fallback тайлбар үүсгэх.
function parseRange(range: string | null): [number, number] | null {
  if (!range) return null
  const m = range.match(/([\d.]+)\s*[-–]\s*([\d.]+)/)
  if (!m) return null
  return [Number(m[1]), Number(m[2])]
}

export type ExplanationContent = StoredExplanation['content']

export type ExplanationInput = {
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

// Rule-based fallback (Gemini ажиллахгүй үед).
export function buildFallbackContent(input: {
  diagnosis_text: string | null
  lab_name: string | null
  lab_value: string | null
  lab_unit: string | null
  reference_range: string | null
}): StoredExplanation['content'] {
  const { lab_name, lab_value, lab_unit, reference_range, diagnosis_text } = input
  const val = lab_value ? Number(lab_value) : null
  const range = parseRange(reference_range)

  let status: 'хэвийн' | 'хэвийнээс өндөр' | 'хэвийнээс бага' | 'тодорхойгүй' = 'тодорхойгүй'
  if (val !== null && range) {
    if (val > range[1]) status = 'хэвийнээс өндөр'
    else if (val < range[0]) status = 'хэвийнээс бага'
    else status = 'хэвийн'
  }

  const labLabel = lab_name ? `${lab_name} ${lab_value ?? ''}${lab_unit ? ' ' + lab_unit : ''}` : 'Шинжилгээ'

  const summary = diagnosis_text
    ? `Таны "${diagnosis_text}" гэсэн дүгнэлт болон ${labLabel} шинжилгээний талаар энгийн тайлбар.`
    : `${labLabel} шинжилгээний талаар энгийн тайлбар.`

  const lab_meaning =
    status === 'хэвийн'
      ? `${labLabel} нь хэвийн хэмжээнд (${reference_range}) байна.`
      : status === 'тодорхойгүй'
      ? `${labLabel}-ийн хэвийн хязгаарыг тодорхойлох мэдээлэл дутуу байна.`
      : `${labLabel} нь ${status} (хэвийн хэмжээ: ${reference_range}).`

  const plain_language =
    status === 'хэвийнээс өндөр'
      ? [
          `${lab_name ?? 'Энэ үзүүлэлт'} хэвийнээс өндөр гарсан нь биеийн тодорхой эрхтний ачаалал, үрэвсэл эсвэл эмийн нөлөөг илэрхийлж болно.`,
          'Ганц үзүүлэлтээр онош тогтоодоггүй — эмч таны бусад шинж тэмдэг, түүхтэй хамт үнэлнэ.',
        ]
      : status === 'хэвийнээс бага'
      ? [
          `${lab_name ?? 'Энэ үзүүлэлт'} хэвийнээс бага байгаа нь тэжээл, шингээлт эсвэл бусад шалтгаантай холбоотой байж болно.`,
          'Эмчтэйгээ уулзаж нэмэлт шинжилгээний шаардлагыг ярилцаарай.',
        ]
      : status === 'хэвийн'
      ? [`${lab_name ?? 'Үзүүлэлт'} хэвийн байгаа нь сайн шинж. Гэхдээ эрүүл мэндийн ерөнхий байдлыг эмч цогцоор үнэлнэ.`]
      : ['Энэ шинжилгээний утгыг зөв тайлбарлахад хэвийн хязгаар, нэгж шаардлагатай.']

  return {
    summary,
    lab_meaning,
    plain_language,
    next_questions: [
      'Энэ үр дүн надад юу гэсэн үг вэ?',
      'Нэмэлт шинжилгээ хийлгэх шаардлагатай юу?',
      'Хэрэглэж буй эм маань үүнд нөлөөлсөн үү?',
    ],
    safety_notes:
      status === 'хэвийнээс өндөр' || status === 'хэвийнээс бага'
        ? ['Хүчтэй өвдөлт, амьсгал давчдах, шарлах зэрэг шинж илэрвэл яаралтай эмчид хандана уу.']
        : ['Шинэ буюу хүндэрсэн шинж тэмдэг илэрвэл эмчтэйгээ холбогдоорой.'],
    disclaimer:
      'Энэ тайлбар нь зөвхөн мэдээллийн зорилготой бөгөөд эмчийн оношийг орлохгүй. Эцсийн шийдвэрийг эмч гаргана.',
  }
}

export function createExplanation(
  patientId: string,
  payload: ExplanationInput,
  content?: ExplanationContent,   // Gemini-ээс ирсэн content; байхгүй бол rule-based
  extracted?: ExtractionResult,   // Gemini Vision-ээс ирсэн зургийн дата; байхгүй бол form-оос
): StoredExplanation {
  const hasAttachment = Boolean(payload.attachment_data_url)
  const range = payload.reference_range
  const val = payload.lab_value ? Number(payload.lab_value) : null
  const parsed = parseRange(range)
  const abnormal = val !== null && parsed ? val < parsed[0] || val > parsed[1] : null

  const fallbackExtracted: ExtractionResult = {
    status: hasAttachment ? 'processed' : 'not_requested',
    model: 'rule-based-demo-v1',
    observations:
      payload.lab_name && payload.lab_value
        ? [
            {
              test_name: payload.lab_name,
              value: payload.lab_value,
              unit: payload.lab_unit,
              reference_range: payload.reference_range,
              abnormal_flag: abnormal,
              source: hasAttachment ? 'form+image' : 'form',
              confidence: 90,
            },
          ]
        : [],
    notes: hasAttachment
      ? ['Зураг хүлээн авлаа. Form талбараас structured дата гаргав.']
      : [],
    ocr_text: null,
  }

  const exp: StoredExplanation = {
    id: `exp-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    patient_id: patientId,
    diagnosis_text: payload.diagnosis_text,
    lab_name: payload.lab_name,
    lab_value: payload.lab_value,
    lab_unit: payload.lab_unit,
    reference_range: payload.reference_range,
    lab_collected_at: payload.lab_collected_at,
    attachment_name: payload.attachment_name,
    attachment_content_type: payload.attachment_content_type,
    attachment_data_url: payload.attachment_data_url,
    patient_question: payload.patient_question,
    content: content ?? buildFallbackContent(payload),
    extracted: extracted ?? fallbackExtracted,
    safety_status: 'reviewed_required',
    created_at: new Date().toISOString(),
  }
  explanations.unshift(exp)
  return exp
}

export function listExplanations(patientId: string): StoredExplanation[] {
  return explanations.filter((e) => e.patient_id === patientId)
}

export function getExplanation(patientId: string, id: string): StoredExplanation | undefined {
  return explanations.find((e) => e.patient_id === patientId && e.id === id)
}
