import { NextResponse } from 'next/server'
import { deleteCase, getCase, updateCase } from '@/lib/clinical-store'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const clinicalCase = getCase(id)
  if (!clinicalCase) return NextResponse.json({ error: 'Тохиолдол олдсонгүй' }, { status: 404 })
  return NextResponse.json(clinicalCase)
}

export async function PUT(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const updated = updateCase(id, body)
  if (!updated) return NextResponse.json({ error: 'Тохиолдол олдсонгүй' }, { status: 404 })
  return NextResponse.json(updated)
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const deleted = deleteCase(id)
  if (!deleted) return NextResponse.json({ error: 'Тохиолдол олдсонгүй' }, { status: 404 })
  return NextResponse.json({ deleted: true, id })
}
