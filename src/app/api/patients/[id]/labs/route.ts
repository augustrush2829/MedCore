import { NextResponse } from 'next/server'
import { addPatientLabs, getPatient, listPatientLabs } from '@/lib/clinical-store'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  if (!getPatient(id)) return NextResponse.json({ error: 'Өвчтөн олдсонгүй' }, { status: 404 })
  return NextResponse.json(listPatientLabs(id))
}

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  if (!getPatient(id)) return NextResponse.json({ error: 'Өвчтөн олдсонгүй' }, { status: 404 })

  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const labs = Array.isArray(body.labs) ? body.labs : []
  const created = addPatientLabs(id, labs, {
    caseId: body.caseId,
    source: body.source ?? 'manual',
    sourceAttachmentId: body.sourceAttachmentId,
  })
  return NextResponse.json({ added: created.length, labs: created }, { status: 201 })
}
