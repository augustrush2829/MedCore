import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'
import { STAFF_TOKEN_COOKIE } from '@/lib/staff-auth'

const BACKEND_BASE_URL = process.env.MEDCORE_BACKEND_URL ?? 'http://localhost:8000'

function backendUrl(path: string) {
  return `${BACKEND_BASE_URL.replace(/\/$/, '')}${path}`
}

export async function POST() {
  const token = (await cookies()).get(STAFF_TOKEN_COOKIE)?.value
  if (token) {
    try {
      await fetch(backendUrl('/auth/logout'), {
        method: 'POST',
        headers: { authorization: `Bearer ${token}` },
        cache: 'no-store',
      })
    } catch {
      // Backend unreachable - still clear the cookie below so the user is logged out client-side.
    }
  }

  const response = NextResponse.json({ ok: true })
  response.cookies.delete(STAFF_TOKEN_COOKIE)
  return response
}
