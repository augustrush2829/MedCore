import { NextResponse } from 'next/server'
import { saveDoctorDecision } from '@/lib/clinical-store'

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const saved = saveDoctorDecision(id, body)
  if (!saved) return NextResponse.json({ error: 'Тохиолдол олдсонгүй' }, { status: 404 })
  return NextResponse.json(saved)
}
