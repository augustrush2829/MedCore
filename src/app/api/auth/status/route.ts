import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'
import { STAFF_TOKEN_COOKIE } from '@/lib/staff-auth'

const BACKEND_BASE_URL = process.env.MEDCORE_BACKEND_URL ?? 'http://localhost:8000'

function backendUrl(path: string) {
  return `${BACKEND_BASE_URL.replace(/\/$/, '')}${path}`
}

async function backendAvailable() {
  try {
    const response = await fetch(backendUrl('/health'), { cache: 'no-store', signal: AbortSignal.timeout(1500) })
    return response.ok
  } catch {
    return false
  }
}

export async function GET() {
  const isBackendAvailable = await backendAvailable()
  if (!isBackendAvailable) {
    return NextResponse.json({ backendAvailable: false, authenticated: false, user: null }, { status: 503 })
  }

  const token = (await cookies()).get(STAFF_TOKEN_COOKIE)?.value
  if (!token) {
    return NextResponse.json({ backendAvailable: true, authenticated: false, user: null })
  }

  const response = await fetch(backendUrl('/auth/me'), {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })

  if (!response.ok) {
    return NextResponse.json({ backendAvailable: true, authenticated: false, user: null })
  }

  return NextResponse.json({ backendAvailable: true, authenticated: true, user: await response.json() })
}
