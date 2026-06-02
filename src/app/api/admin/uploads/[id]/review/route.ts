import { NextResponse } from 'next/server'
import { markUploadReviewed } from '@/lib/clinical-store'

export async function PATCH(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const upload = markUploadReviewed(id)
  if (!upload) return NextResponse.json({ error: 'Upload олдсонгүй' }, { status: 404 })
  return NextResponse.json(upload)
}
