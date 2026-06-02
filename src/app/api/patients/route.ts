import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'
import { normalizePatient, toBackendPatientCreate } from '@/lib/backend-normalize'

export async function GET(req: Request) {
  const { response, body } = await backendJson<unknown[]>(req, '/patients')
  if (!response.ok) return NextResponse.json(body, { status: response.status })
  return NextResponse.json(body.map((item) => normalizePatient(item as never)))
}

export async function POST(req: Request) {
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  if (!body.name || !(body.dateOfBirth || body.dob)) {
    return NextResponse.json({ error: 'name болон dateOfBirth шаардлагатай' }, { status: 400 })
  }

  const backendReq = new Request(req.url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toBackendPatientCreate(body)),
  })
  const { response, body: created } = await backendJson<unknown>(backendReq, '/patients')
  if (!response.ok) return NextResponse.json(created, { status: response.status })
  return NextResponse.json(normalizePatient(created as never), { status: 201 })
}
