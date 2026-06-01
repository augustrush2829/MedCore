import { NextResponse } from 'next/server'
import { verifyToken, listExplanations, createExplanation } from '@/lib/patient-store'
import { toApiExplanation } from '@/lib/patient-serialize'
import { generateExplanationContent, extractFromImage } from '@/lib/ai/patient-explainer'

// GET /api/patient-portal/explanations  → тухайн өвчтөний тайлбарууд
export async function GET(req: Request) {
  const patientId = verifyToken(req.headers.get('authorization'))
  if (!patientId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const items = listExplanations(patientId).map(toApiExplanation)
  return NextResponse.json(items)
}

// POST /api/patient-portal/explanations  → шинэ тайлбар үүсгэх (AI extraction demo)
export async function POST(req: Request) {
  const patientId = verifyToken(req.headers.get('authorization'))
  if (!patientId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  let payload
  try {
    payload = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const input = {
    diagnosis_text: payload.diagnosis_text ?? null,
    lab_name: payload.lab_name ?? null,
    lab_value: payload.lab_value ?? null,
    lab_unit: payload.lab_unit ?? null,
    reference_range: payload.reference_range ?? null,
    lab_collected_at: payload.lab_collected_at ?? null,
    attachment_name: payload.attachment_name ?? null,
    attachment_content_type: payload.attachment_content_type ?? null,
    attachment_data_url: payload.attachment_data_url ?? null,
    patient_question: payload.patient_question ?? null,
  }

  let created
  if (input.attachment_data_url) {
    // Зураг байвал Gemini Vision-аар уншиж lab утга гаргаж аваад тайлбарлана
    const { content, extracted } = await extractFromImage(input, input.attachment_data_url)
    created = createExplanation(patientId, input, content, extracted)
  } else {
    // Зураггүй бол текст promtoor тайлбар үүсгэнэ
    const { content } = await generateExplanationContent(input)
    created = createExplanation(patientId, input, content)
  }

  return NextResponse.json(toApiExplanation(created))
}
