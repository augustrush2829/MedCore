import { NextResponse } from 'next/server'
import { toggleAdminUser } from '@/lib/clinical-store'

export async function PATCH(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const user = toggleAdminUser(id)
  if (!user) return NextResponse.json({ error: 'Хэрэглэгч олдсонгүй' }, { status: 404 })
  return NextResponse.json(user)
}
