import { proxyBackend } from '@/lib/backend-api-proxy'

// GET /api/patient-portal/explanations  → тухайн өвчтөний тайлбарууд
export async function GET(req: Request) {
  return proxyBackend(req, '/patient-portal/explanations', 'patient')
}

// POST /api/patient-portal/explanations  → шинэ тайлбар үүсгэх
export async function POST(req: Request) {
  return proxyBackend(req, '/patient-portal/explanations', 'patient')
}
