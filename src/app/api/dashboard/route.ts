import { proxyBackend } from '@/lib/backend-api-proxy'

export async function GET(req: Request) {
  return proxyBackend(req, '/dashboard')
}
