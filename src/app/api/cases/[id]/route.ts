import { NextResponse } from 'next/server'
import { backendJson, proxyBackend } from '@/lib/backend-api-proxy'
import { normalizeCase, toBackendCaseUpdate } from '@/lib/backend-normalize'

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const { response, body } = await backendJson<unknown>(req, `/cases/${id}`)
  if (!response.ok) return NextResponse.json(body, { status: response.status })
  const clinicalCase = normalizeCase(body as never)
  if (clinicalCase.patientName) return NextResponse.json(clinicalCase)

  const patientResult = await backendJson<{ name: string }>(req, `/patients/${clinicalCase.patientId}`)
  return NextResponse.json({
    ...clinicalCase,
    patientName: patientResult.response.ok ? patientResult.body.name : '',
  })
}

export async function PUT(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }
  const backendReq = new Request(req.url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toBackendCaseUpdate(body)),
  })
  const { response, body: updated } = await backendJson<unknown>(backendReq, `/cases/${id}`)
  if (!response.ok) return NextResponse.json(updated, { status: response.status })
  const clinicalCase = normalizeCase(updated as never)
  if (clinicalCase.patientName) return NextResponse.json(clinicalCase)
  const patientResult = await backendJson<{ name: string }>(req, `/patients/${clinicalCase.patientId}`)
  return NextResponse.json({
    ...clinicalCase,
    patientName: patientResult.response.ok ? patientResult.body.name : '',
  })
}

export async function DELETE(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return proxyBackend(req, `/cases/${id}`)
}
