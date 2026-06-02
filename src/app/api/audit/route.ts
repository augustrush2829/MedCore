import { NextResponse } from 'next/server'
import { listAuditEvents } from '@/lib/clinical-store'

export async function GET() {
  return NextResponse.json(listAuditEvents())
}
