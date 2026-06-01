import { NextResponse } from 'next/server'
import { verifyToken, getExplanation } from '@/lib/patient-store'

// GET /api/patient-portal/explanations/{id}/image → хадгалсан зургийг буцаах
export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const patientId = verifyToken(req.headers.get('authorization'))
  if (!patientId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  const exp = getExplanation(patientId, id)
  if (!exp?.attachment_data_url) {
    return NextResponse.json({ error: 'Зураг олдсонгүй' }, { status: 404 })
  }

  // data URL → binary blob
  const match = exp.attachment_data_url.match(/^data:(.+?);base64,(.*)$/)
  if (!match) return NextResponse.json({ error: 'Зургийн формат буруу' }, { status: 422 })

  const contentType = match[1]
  const buffer = Buffer.from(match[2], 'base64')
  return new NextResponse(new Uint8Array(buffer), {
    headers: { 'Content-Type': contentType, 'Cache-Control': 'private, max-age=60' },
  })
}
