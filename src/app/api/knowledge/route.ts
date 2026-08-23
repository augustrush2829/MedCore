import { NextResponse } from 'next/server'
import { getDatasets, allSymptoms } from '@/lib/knowledge/datasets'

// GET /api/knowledge          → датасетуудын статистик
// GET /api/knowledge?symptoms → бүх симптомын жагсаалт (autocomplete)
// GET /api/knowledge?icd=A00  → ICD кодын нэр
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)

  if (searchParams.has('symptoms')) {
    return NextResponse.json({ symptoms: allSymptoms() })
  }

  const icd = searchParams.get('icd')
  if (icd) {
    const { icdIndex } = getDatasets()
    return NextResponse.json({ code: icd, name: icdIndex[icd] ?? null })
  }

  const { diseases, symptomWeight, edoctor, icdIndex } = getDatasets()
  return NextResponse.json({
    diseaseSymptomRows: diseases.length,
    distinctSymptoms: symptomWeight.size,
    edoctorDiseases: edoctor.length,
    icdCodes: Object.keys(icdIndex).length,
  })
}
