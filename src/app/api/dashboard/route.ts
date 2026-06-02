import { NextResponse } from 'next/server'
import { dashboardSummary } from '@/lib/clinical-store'

export async function GET() {
  return NextResponse.json(dashboardSummary())
}
