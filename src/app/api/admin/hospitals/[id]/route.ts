import { NextResponse } from 'next/server'
import { toggleHospital } from '@/lib/clinical-store'

export async function PATCH(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const hospital = toggleHospital(id)
  if (!hospital) return NextResponse.json({ error: 'Hospital олдсонгүй' }, { status: 404 })
  return NextResponse.json(hospital)
}
