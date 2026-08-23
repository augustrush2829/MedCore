import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'
import { normalizeCase, toBackendCaseCreate } from '@/lib/backend-normalize'

export async function GET(req: Request) {
  const { response, body } = await backendJson<unknown[]>(req, '/cases')
  if (!response.ok) return NextResponse.json(body, { status: response.status })
  const patients = await backendJson<Array<{ id: string; name: string }>>(req, '/patients')
  const patientNames = new Map(patients.response.ok ? patients.body.map((patient) => [patient.id, patient.name]) : [])
  return NextResponse.json(body.map((item) => {
    const clinicalCase = normalizeCase(item as never)
    return { ...clinicalCase, patientName: clinicalCase.patientName || patientNames.get(clinicalCase.patientId) || '' }
  }))
}

export async function POST(req: Request) {
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const backendReq = new Request(req.url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toBackendCaseCreate(body)),
  })
  const { response, body: created } = await backendJson<unknown>(backendReq, '/cases')
  if (!response.ok) return NextResponse.json(created, { status: response.status })
  return NextResponse.json(normalizeCase(created as never), { status: 201 })
}
