import { NextResponse } from 'next/server'
import { runDifferentialDiagnosis } from '@/lib/knowledge/diagnosis-engine'

// POST /api/diagnosis  { symptoms: string[] }
// Бодит датасет дээр тулгуурлан differential diagnosis буцаана
export async function POST(req: Request) {
  let body: { symptoms?: string[] }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const symptoms = Array.isArray(body.symptoms) ? body.symptoms : []
  if (symptoms.length === 0) {
    return NextResponse.json({ error: 'symptoms массив шаардлагатай' }, { status: 400 })
  }

  const matches = runDifferentialDiagnosis(symptoms)

  return NextResponse.json({
    inputSymptoms: symptoms,
    matchCount: matches.length,
    differentialDiagnosis: matches,
    doctorConfirmationRequired: true,
    disclaimer: 'Энэ нь датасет дээр суурилсан санал. Эцсийн оношийг эмч баталгаажуулна.',
  })
}
