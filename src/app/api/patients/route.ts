import { NextResponse } from 'next/server'
import { createPatient, listPatients } from '@/lib/clinical-store'

export async function GET() {
  return NextResponse.json(listPatients())
}

export async function POST(req: Request) {
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  if (!body.name || !(body.dateOfBirth || body.dob)) {
    return NextResponse.json({ error: 'name болон dateOfBirth шаардлагатай' }, { status: 400 })
  }

  return NextResponse.json(createPatient(body), { status: 201 })
}
