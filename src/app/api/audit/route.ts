import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'

export async function GET(req: Request) {
  const { response, body } = await backendJson<Array<{
    id: string
    actor_user_id: string | null
    action: string
    entity_type: string
    entity_id: string
    created_at: string
  }>>(req, '/audit')
  if (!response.ok) return NextResponse.json(body, { status: response.status })
  return NextResponse.json(body.map((event) => ({
    id: event.id,
    actor: event.actor_user_id ?? 'system',
    action: event.action,
    entity: `${event.entity_type}/${event.entity_id}`,
    timestamp: event.created_at,
    type: event.action.includes('create') ? 'create' : event.action.includes('update') ? 'update' : event.action.includes('decision') ? 'decision' : 'view',
  })))
}
