import { NextResponse } from 'next/server'
import { proxyBackend } from '@/lib/backend-api-proxy'

export async function POST(req: Request) {
  return proxyBackend(req, '/admin/users')
}
