import { proxyBackend } from '@/lib/backend-api-proxy'

// POST /api/patient-portal/login  { login_identifier, password }
export async function POST(req: Request) {
  return proxyBackend(req, '/patient-portal/login', 'none')
}
