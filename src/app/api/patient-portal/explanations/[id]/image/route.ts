import { proxyBackend } from '@/lib/backend-api-proxy'

// GET /api/patient-portal/explanations/{id}/image → хадгалсан зургийг буцаах
export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return proxyBackend(req, `/patient-portal/explanations/${id}/image`, 'patient')
}
