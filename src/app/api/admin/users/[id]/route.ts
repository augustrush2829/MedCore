import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const users = await backendJson<Array<{ id: string; status?: string }>>(req, '/admin/users')
  if (!users.response.ok) return NextResponse.json(users.body, { status: users.response.status })
  const current = users.body.find((user) => user.id === id)
  if (!current) return NextResponse.json({ error: 'Хэрэглэгч олдсонгүй' }, { status: 404 })
  const backendReq = new Request(req.url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: current.status === 'disabled' ? 'active' : 'disabled' }),
  })
  const result = await backendJson<unknown>(backendReq, `/admin/users/${id}`)
  return NextResponse.json(result.body, { status: result.response.status })
}
