import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'
import { normalizeCase, normalizePatient } from '@/lib/backend-normalize'

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const patientResult = await backendJson<unknown>(req, `/patients/${id}`)
  if (!patientResult.response.ok) return NextResponse.json(patientResult.body, { status: patientResult.response.status })

  const casesResult = await backendJson<unknown[]>(req, '/cases')
  const cases = casesResult.response.ok
    ? casesResult.body.map((item) => normalizeCase(item as never)).filter((clinicalCase) => clinicalCase.patientId === id)
    : []
  const labs = cases.flatMap((clinicalCase) =>
    clinicalCase.labResults.map((lab) => ({
      ...lab,
      patientId: id,
      caseId: clinicalCase.id,
      source: 'manual' as const,
      createdAt: clinicalCase.createdAt,
    }))
  )

  return NextResponse.json({ patient: normalizePatient(patientResult.body as never), cases, labs })
}
