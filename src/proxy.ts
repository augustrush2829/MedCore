import { NextResponse, type NextRequest } from 'next/server'
import { STAFF_TOKEN_COOKIE } from '@/lib/staff-auth'

const BACKEND_BASE_URL = process.env.MEDCORE_BACKEND_URL ?? 'http://localhost:8000'

const protectedPagePrefixes = ['/dashboard', '/patients', '/cases', '/admin', '/audit']
const protectedApiPrefixes = ['/api/dashboard', '/api/patients', '/api/cases', '/api/admin', '/api/audit']

function backendUrl(path: string) {
  return `${BACKEND_BASE_URL.replace(/\/$/, '')}${path}`
}

function isProtected(pathname: string) {
  return protectedPagePrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)) ||
    protectedApiPrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))
}

function isApi(pathname: string) {
  return pathname.startsWith('/api/')
}

async function backendAvailable() {
  try {
    const response = await fetch(backendUrl('/health'), { cache: 'no-store', signal: AbortSignal.timeout(1000) })
    return response.ok
  } catch {
    return false
  }
}

async function tokenValid(token: string) {
  try {
    const response = await fetch(backendUrl('/auth/me'), {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
      signal: AbortSignal.timeout(1500),
    })
    return response.ok
  } catch {
    return false
  }
}

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl
  if (!isProtected(pathname)) return NextResponse.next()

  const available = await backendAvailable()
  if (!available) {
    if (isApi(pathname)) {
      return NextResponse.json({ error: 'Backend API холбогдохгүй байна' }, { status: 503 })
    }

    const loginUrl = req.nextUrl.clone()
    loginUrl.pathname = '/'
    loginUrl.searchParams.set('backend', 'unavailable')
    return NextResponse.redirect(loginUrl)
  }

  const token = req.cookies.get(STAFF_TOKEN_COOKIE)?.value
  const authenticated = token ? await tokenValid(token) : false
  if (authenticated) return NextResponse.next()

  if (isApi(pathname)) {
    return NextResponse.json({ error: 'Backend ажиллаж байгаа тул эмчийн backend login шаардлагатай' }, { status: 401 })
  }

  const loginUrl = req.nextUrl.clone()
  loginUrl.pathname = '/'
  loginUrl.searchParams.set('next', pathname)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  matcher: ['/dashboard/:path*', '/patients/:path*', '/cases/:path*', '/admin/:path*', '/audit/:path*', '/api/:path*'],
}
