import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'
import { toBackendLab } from '@/lib/backend-normalize'

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const result = await backendJson<unknown[]>(req, `/patients/${id}/labs`)
  return NextResponse.json(result.body, { status: result.response.status })
}

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const backendReq = new Request(req.url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      case_id: body.caseId,
      labs: (Array.isArray(body.labs) ? body.labs : []).map(toBackendLab),
    }),
  })
  const result = await backendJson<unknown>(backendReq, `/patients/${id}/labs`)
  return NextResponse.json(result.body, { status: result.response.status })
}
