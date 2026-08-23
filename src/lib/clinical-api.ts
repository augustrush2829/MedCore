import type { ClinicalCase, Patient } from '@/types'
import type { AdminUser, AuditEvent, Hospital, UploadReview } from './clinical-store'

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch (caught) {
    const detail = caught instanceof Error ? ` (${caught.message})` : ''
    throw new Error(`Backend API холбогдохгүй байна${detail}`)
  }

  if (!response.ok) {
    let message = 'Backend API алдаа гарлаа'
    try {
      const body = await response.json() as { error?: string; message?: string }
      message = body.error || body.message || message
    } catch {
      // Status is still shown below.
    }
    throw new Error(`${message} (HTTP ${response.status}${response.statusText ? ` ${response.statusText}` : ''})`)
  }

  return response.json() as Promise<T>
}

export type DashboardPayload = {
  currentUser: { id: string; name: string; email: string; role: string; organization: string; specialty: string }
  stats: { todayCases: number; newCases: number; aiComplete: number; redFlags: number; patients: number }
  cases: ClinicalCase[]
}

export type AdminPayload = {
  hospitals: Hospital[]
  users: AdminUser[]
  uploads: UploadReview[]
  stats: { hospitals: number; users: number; activeUsers: number; patients: number; cases: number; uploads: number; review: number; failed: number }
}

export const clinicalApi = {
  dashboard: () => api<DashboardPayload>('/api/dashboard'),
  patients: () => api<Patient[]>('/api/patients'),
  patient: (id: string) => api<{ patient: Patient; cases: ClinicalCase[] }>(`/api/patients/${id}`),
  createPatient: (payload: unknown) => api<Patient>('/api/patients', jsonInit('POST', payload)),
  cases: () => api<ClinicalCase[]>('/api/cases'),
  createCase: (payload: unknown) => api<ClinicalCase>('/api/cases', jsonInit('POST', payload)),
  case: (id: string) => api<ClinicalCase>(`/api/cases/${id}`),
  updateCase: (id: string, payload: unknown) => api<ClinicalCase>(`/api/cases/${id}`, jsonInit('PUT', payload)),
  deleteCase: (id: string) => api<{ deleted: true; id: string }>(`/api/cases/${id}`, { method: 'DELETE' }),
  analyzeCase: (id: string) => api<ClinicalCase>(`/api/cases/${id}/analyze`, jsonInit('POST', {})),
  extractLabs: (id: string) => api<{ added: number; extracted: number; patientLabsAdded: number; case: ClinicalCase }>(`/api/cases/${id}/extract-labs`, jsonInit('POST', {})),
  saveDecision: (id: string, payload: unknown) => api(`/api/cases/${id}/decision`, jsonInit('POST', payload)),
  admin: () => api<AdminPayload>('/api/admin'),
  createHospital: (payload: unknown) => api<Hospital>('/api/admin/hospitals', jsonInit('POST', payload)),
  toggleHospital: (id: string) => api<Hospital>(`/api/admin/hospitals/${id}`, jsonInit('PATCH', {})),
  createUser: (payload: unknown) => api<AdminUser>('/api/admin/users', jsonInit('POST', payload)),
  toggleUser: (id: string) => api<AdminUser>(`/api/admin/users/${id}`, jsonInit('PATCH', {})),
  markUploadReviewed: (id: string) => api<UploadReview>(`/api/admin/uploads/${id}/review`, jsonInit('PATCH', {})),
  audit: () => api<AuditEvent[]>('/api/audit'),
}

function jsonInit(method: string, payload: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }
}
