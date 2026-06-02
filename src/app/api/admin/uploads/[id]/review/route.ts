import { backendJson } from '@/lib/backend-api-proxy'

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const backendReq = new Request(req.url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extraction_status: 'processed' }),
  })
  const result = await backendJson<unknown>(backendReq, `/admin/portal-explanations/${id}`)
  return Response.json(result.body, { status: result.response.status })
}
