import 'server-only'

import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'
import { STAFF_TOKEN_COOKIE } from '@/lib/staff-auth'

const BACKEND_BASE_URL = process.env.MEDCORE_BACKEND_URL ?? 'http://localhost:8000'

function backendUrl(path: string) {
  return `${BACKEND_BASE_URL.replace(/\/$/, '')}${path}`
}

type AuthMode = 'staff' | 'patient' | 'none'

export async function backendRequest(req: Request, path: string, auth: AuthMode = 'staff') {
  const headers = new Headers()
  const contentType = req.headers.get('content-type')
  if (contentType) headers.set('content-type', contentType)

  if (auth === 'staff') {
    const token = (await cookies()).get(STAFF_TOKEN_COOKIE)?.value
    if (token) headers.set('authorization', `Bearer ${token}`)
  } else if (auth === 'patient') {
    const authorization = req.headers.get('authorization')
    if (authorization) headers.set('authorization', authorization)
  }

  const method = req.method
  const init: RequestInit = {
    method,
    headers,
    cache: 'no-store',
  }
  if (!['GET', 'HEAD'].includes(method)) {
    init.body = await req.text()
  }

  return fetch(backendUrl(path), init)
}

export async function backendJson<T>(req: Request, path: string, auth: AuthMode = 'staff') {
  const response = await backendRequest(req, path, auth)
  const body = await response.json().catch(() => null)
  return { response, body: body as T }
}

export async function proxyBackend(req: Request, path: string, auth: AuthMode = 'staff') {
  let response: Response
  try {
    response = await backendRequest(req, path, auth)
  } catch {
    return NextResponse.json({ error: 'Backend API холбогдохгүй байна' }, { status: 503 })
  }

  const headers = new Headers()
  const contentType = response.headers.get('content-type')
  if (contentType) headers.set('content-type', contentType)

  return new NextResponse(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  })
}

