import { NextResponse } from 'next/server'
import { createHospital } from '@/lib/clinical-store'

export async function POST(req: Request) {
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }
  return NextResponse.json(createHospital(body), { status: 201 })
}
