import { NextResponse } from 'next/server'
import { backendJson } from '@/lib/backend-api-proxy'

export async function GET(req: Request) {
  const overview = await backendJson<{
    patients_total: number
    cases_total: number
    portal_uploads_total: number
    portal_uploads_requiring_review: number
  }>(req, '/admin/overview')
  if (!overview.response.ok) return NextResponse.json(overview.body, { status: overview.response.status })

  const users = await backendJson<Array<{ id: string; name: string; email: string; role: string }>>(req, '/admin/users')
  const uploads = await backendJson<Array<{
    id: string
    patient_name: string
    patient_id: string
    lab_name: string | null
    lab_collected_at: string | null
    extraction_status: 'processed' | 'requires_review' | 'failed'
    extracted_lab_data?: { ocr_languages?: string | null }
    has_attachment: boolean
  }>>(req, '/admin/portal-explanations')

  return NextResponse.json({
    hospitals: [],
    users: users.response.ok
      ? users.body.map((user) => ({ ...user, status: 'active', lastSeen: '' }))
      : [],
    uploads: uploads.response.ok
      ? uploads.body.map((upload) => ({
          id: upload.id,
          patientName: upload.patient_name,
          patientId: upload.patient_id,
          labName: upload.lab_name ?? '',
          collectedAt: upload.lab_collected_at ?? '',
          extractionStatus: upload.extraction_status,
          ocrLanguages: upload.extracted_lab_data?.ocr_languages ?? '',
          hasImage: upload.has_attachment,
        }))
      : [],
    stats: {
      hospitals: 0,
      users: users.response.ok ? users.body.length : 0,
      activeUsers: users.response.ok ? users.body.length : 0,
      patients: overview.body.patients_total,
      cases: overview.body.cases_total,
      uploads: overview.body.portal_uploads_total,
      review: overview.body.portal_uploads_requiring_review,
      failed: uploads.response.ok ? uploads.body.filter((upload) => upload.extraction_status === 'failed').length : 0,
    },
  })
}
