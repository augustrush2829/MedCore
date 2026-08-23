import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const { response, body } = await backendJson<unknown>(req, `/cases/${id}/ai/differential-diagnosis`)
  return NextResponse.json(body, { status: response.status })
}
