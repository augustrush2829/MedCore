import { NextResponse } from 'next/server'
import { analyzeCase } from '@/lib/clinical-store'

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const clinicalCase = analyzeCase(id)
  if (!clinicalCase) return NextResponse.json({ error: 'Тохиолдол олдсонгүй' }, { status: 404 })
  return NextResponse.json(clinicalCase)
}
