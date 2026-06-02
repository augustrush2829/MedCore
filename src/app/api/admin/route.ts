import { NextResponse } from 'next/server'
import { adminOverview } from '@/lib/clinical-store'

export async function GET() {
  return NextResponse.json(adminOverview())
}
