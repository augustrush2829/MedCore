import { NextResponse } from 'next/server'
import { createCase, listCases } from '@/lib/clinical-store'

export async function GET() {
  return NextResponse.json(listCases())
}

export async function POST(req: Request) {
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const created = createCase(body)
  if (!created) return NextResponse.json({ error: 'Өвчтөн олдсонгүй' }, { status: 404 })
  return NextResponse.json(created, { status: 201 })
}
