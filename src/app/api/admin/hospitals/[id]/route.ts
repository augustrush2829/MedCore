import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const organizations = await backendJson<Array<{ id: string; status: string }>>(req, '/admin/organizations')
  if (!organizations.response.ok) return NextResponse.json(organizations.body, { status: organizations.response.status })
  const current = organizations.body.find((organization) => organization.id === id)
  if (!current) return NextResponse.json({ error: 'Hospital олдсонгүй' }, { status: 404 })
  const backendReq = new Request(req.url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: current.status === 'disabled' ? 'active' : 'disabled' }),
  })
  const result = await backendJson<unknown>(backendReq, `/admin/organizations/${id}`)
  return NextResponse.json(result.body, { status: result.response.status })
}
