import { NextResponse } from 'next/server'
import { authenticate, makeToken } from '@/lib/patient-store'

// POST /api/patient-portal/login  { login_identifier, password }
export async function POST(req: Request) {
  let body: { login_identifier?: string; password?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const user = authenticate(body.login_identifier ?? '', body.password ?? '')
  if (!user) {
    return NextResponse.json({ error: 'Нэвтрэх мэдээлэл буруу байна' }, { status: 401 })
  }

  return NextResponse.json({
    access_token: makeToken(user.id),
    token_type: 'bearer',
    patient: user,
  })
}
