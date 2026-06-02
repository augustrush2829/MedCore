import { NextResponse } from 'next/server'
import { getPatient, listCases, listPatientLabs } from '@/lib/clinical-store'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const patient = getPatient(id)
  if (!patient) return NextResponse.json({ error: 'Өвчтөн олдсонгүй' }, { status: 404 })
  const cases = listCases().filter((clinicalCase) => clinicalCase.patientId === id)
  const labs = listPatientLabs(id)
  return NextResponse.json({ patient, cases, labs })
}
