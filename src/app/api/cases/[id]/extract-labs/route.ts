import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'
import { normalizeCase } from '@/lib/backend-normalize'

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const result = await backendJson<{
    added: number
    extracted: number
    patientLabsAdded: number
    case?: unknown
    extractions?: string[]
  }>(req, `/cases/${id}/extract-labs`)
  if (!result.response.ok) return NextResponse.json(result.body, { status: result.response.status })
  return NextResponse.json({
    ...result.body,
    case: result.body.case ? normalizeCase(result.body.case as never) : undefined,
  })
}
