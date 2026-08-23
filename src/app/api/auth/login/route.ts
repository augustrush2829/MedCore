import { NextResponse } from 'next/server'
import { STAFF_TOKEN_COOKIE } from '@/lib/staff-auth'

const BACKEND_BASE_URL = process.env.MEDCORE_BACKEND_URL ?? 'http://localhost:8000'

function backendUrl(path: string) {
  return `${BACKEND_BASE_URL.replace(/\/$/, '')}${path}`
}

export async function POST(req: Request) {
  let body: { email?: string; password?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const response = await fetch(backendUrl('/auth/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: body.email, password: body.password }),
    cache: 'no-store',
  })

  if (!response.ok) {
    let message = 'Нэвтрэх нэр эсвэл нууц үг буруу байна'
    try {
      const error = await response.json() as { detail?: string }
      message = error.detail || message
    } catch {
      // Keep default message.
    }
    return NextResponse.json({ error: message }, { status: response.status })
  }

  const result = await response.json() as { access_token: string; token_type: string; user: unknown }
  const next = NextResponse.json(result)
  const isHttps = new URL(req.url).protocol === 'https:'
  next.cookies.set(STAFF_TOKEN_COOKIE, result.access_token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production' && isHttps,
    path: '/',
    maxAge: 60 * 60,
  })
  return next
}
