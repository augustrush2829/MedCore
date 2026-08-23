import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  let body: { decision?: string; rationale?: string; editedDiagnosis?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const backendReq = new Request(req.url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      decision: body.decision ?? 'accept',
      rationale: body.rationale ?? '',
      edited_diagnosis: body.editedDiagnosis,
    }),
  })
  const { response, body: result } = await backendJson<unknown>(backendReq, `/cases/${id}/doctor-decision`)
  return NextResponse.json(result, { status: response.status })
}
