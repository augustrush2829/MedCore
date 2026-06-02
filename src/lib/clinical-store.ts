import 'server-only'
import type { ClinicalCase, LabResult, Patient, PatientLabResult } from '@/types'
import { currentUser, seedCases, seedPatients } from './seed-data'

export type AdminUser = {
  id: string
  name: string
  email: string
  role: 'doctor' | 'pharmacist' | 'admin' | 'auditor'
  status: 'active' | 'disabled'
  lastSeen: string
}

export type UploadReview = {
  id: string
  patientName: string
  patientId: string
  labName: string
  collectedAt: string
  extractionStatus: 'processed' | 'requires_review' | 'failed'
  ocrLanguages: string
  hasImage: boolean
}

export type Hospital = {
  id: string
  name: string
  plan: string
  status: 'active' | 'disabled'
  adminName: string
  adminEmail: string
  doctors: number
  patients: number
}

export type AuditEvent = {
  id: string
  actor: string
  action: string
  entity: string
  timestamp: string
  type: 'view' | 'decision' | 'create' | 'ai_request' | 'admin' | 'update'
}

type Store = {
  patients: Patient[]
  cases: ClinicalCase[]
  patientLabs: PatientLabResult[]
  hospitals: Hospital[]
  users: AdminUser[]
  uploads: UploadReview[]
  auditEvents: AuditEvent[]
}

const globalStore = globalThis as typeof globalThis & { __medcoreClinicalStore?: Store }

function nowDisplay() {
  return new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Ulaanbaatar' }).replace('T', ' ')
}

function todayDate() {
  return new Date().toISOString().slice(0, 10)
}

function seedPatientLabsFromCases(cases: ClinicalCase[]) {
  return cases.flatMap((clinicalCase) =>
    clinicalCase.labResults.map((lab) => ({
      ...lab,
      id: `patient-${lab.id}`,
      patientId: clinicalCase.patientId,
      caseId: clinicalCase.id,
      source: 'manual' as const,
      createdAt: clinicalCase.createdAt,
    }))
  )
}

function createSeedStore(): Store {
  const useDemoData = process.env.MEDCORE_DEMO_DATA === 'true'
  const cases = useDemoData ? [...seedCases] : []
  const patients = useDemoData ? [...seedPatients] : []
  return {
    patients,
    cases,
    patientLabs: seedPatientLabsFromCases(cases),
    hospitals: [
      ...(useDemoData
        ? [
            { id: 'org1', name: 'Улаанбаатар Эмнэлэг №1', plan: 'mvp', status: 'active' as const, adminName: 'Байгууллагын админ', adminEmail: 'admin@clinic.mn', doctors: 1, patients: seedPatients.length },
            { id: 'org2', name: 'Дархан Клиник', plan: 'mvp', status: 'disabled' as const, adminName: 'Демо админ', adminEmail: 'admin@darkhan.mn', doctors: 0, patients: 0 },
          ]
        : []),
    ],
    users: useDemoData
      ? [
          { id: 'u1', name: 'Д. Батболд', email: 'batbold@clinic.mn', role: 'doctor', status: 'active', lastSeen: '2026-06-01 18:22' },
          { id: 'u2', name: 'Чанарын хянагч', email: 'auditor@clinic.mn', role: 'auditor', status: 'active', lastSeen: '2026-06-01 16:10' },
          { id: 'u3', name: 'Байгууллагын админ', email: 'admin@clinic.mn', role: 'admin', status: 'active', lastSeen: '2026-06-01 19:01' },
          { id: 'u4', name: 'Эмийн санч', email: 'pharmacist@clinic.mn', role: 'pharmacist', status: 'disabled', lastSeen: '2026-05-29 11:35' },
        ]
      : [],
    uploads: useDemoData
      ? [
          { id: 'px1', patientName: 'Б. Энхжаргал', patientId: 'p1', labName: 'ALT', collectedAt: '2026-06-01', extractionStatus: 'processed', ocrLanguages: 'eng+mon', hasImage: true },
          { id: 'px2', patientName: 'Д. Батсүх', patientId: 'p2', labName: 'Troponin', collectedAt: '2026-05-31', extractionStatus: 'requires_review', ocrLanguages: 'eng+mon', hasImage: true },
          { id: 'px3', patientName: 'Н. Оюунчимэг', patientId: 'p3', labName: 'CBC', collectedAt: '2026-05-30', extractionStatus: 'failed', ocrLanguages: 'eng+mon', hasImage: true },
        ]
      : [],
    auditEvents: useDemoData
      ? [
          { id: 'a1', actor: 'Д. Батболд', action: 'AI хариулт харсан', entity: 'case/c1', timestamp: '2026-05-31 09:35:12', type: 'view' },
          { id: 'a2', actor: 'Д. Батболд', action: 'Doctor decision: зөвшөөрсөн', entity: 'case/c1', timestamp: '2026-05-31 09:48:05', type: 'decision' },
          { id: 'a3', actor: 'Д. Батболд', action: 'Өвчтөн үүсгэсэн', entity: 'patient/p3', timestamp: '2026-05-31 11:00:22', type: 'create' },
          { id: 'a4', actor: 'Д. Батболд', action: 'AI шинжилгээ хүсэлт илгээсэн', entity: 'case/c2', timestamp: '2026-05-31 10:20:00', type: 'ai_request' },
          { id: 'a5', actor: 'А. Оюун (Admin)', action: 'Хэрэглэгч урилга илгээсэн', entity: 'user/new', timestamp: '2026-05-30 15:12:33', type: 'admin' },
          { id: 'a6', actor: 'Д. Батболд', action: 'Тохиолдол үүсгэсэн', entity: 'case/c1', timestamp: '2026-05-31 09:00:00', type: 'create' },
        ]
      : [],
  }
}

function store() {
  globalStore.__medcoreClinicalStore ??= createSeedStore()
  const data = globalStore.__medcoreClinicalStore as Store & Partial<Store>
  data.patients ??= []
  data.cases ??= []
  data.patientLabs ??= seedPatientLabsFromCases(data.cases)
  data.hospitals ??= []
  data.users ??= []
  data.uploads ??= []
  data.auditEvents ??= []
  return data as Store
}

function nextId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

export function addAuditEvent(event: Omit<AuditEvent, 'id' | 'timestamp'> & { timestamp?: string }) {
  const item: AuditEvent = {
    id: nextId('audit'),
    timestamp: event.timestamp ?? nowDisplay(),
    actor: event.actor,
    action: event.action,
    entity: event.entity,
    type: event.type,
  }
  store().auditEvents.unshift(item)
  return item
}

function ageFromDob(dob: string) {
  const birth = new Date(dob)
  if (Number.isNaN(birth.getTime())) return 0
  const now = new Date()
  let age = now.getFullYear() - birth.getFullYear()
  const monthDelta = now.getMonth() - birth.getMonth()
  if (monthDelta < 0 || (monthDelta === 0 && now.getDate() < birth.getDate())) age -= 1
  return age
}

export function listPatients() {
  return store().patients
}

export function getPatient(id: string) {
  return store().patients.find((patient) => patient.id === id)
}

function patientLabKey(lab: Pick<PatientLabResult, 'patientId' | 'testName' | 'collectedAt'>) {
  return `${lab.patientId}::${lab.testName.toLowerCase()}::${lab.collectedAt || 'date-review'}`
}

export function listPatientLabs(patientId: string) {
  return store().patientLabs.filter((lab) => lab.patientId === patientId)
}

export function addPatientLabs(
  patientId: string,
  labs: LabResult[],
  opts: { caseId?: string; source: PatientLabResult['source']; sourceAttachmentId?: string },
) {
  const data = store()
  const existing = new Set(data.patientLabs.map(patientLabKey))
  const created = labs
    .map((lab) => ({
      ...lab,
      id: `patient-lab-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
      patientId,
      caseId: opts.caseId,
      source: opts.source,
      sourceAttachmentId: opts.sourceAttachmentId,
      createdAt: new Date().toISOString(),
    }))
    .filter((lab) => !existing.has(patientLabKey(lab)))

  data.patientLabs.unshift(...created)
  if (created.length > 0) {
    addAuditEvent({ actor: currentUser.name, action: `${created.length} patient lab нэмсэн`, entity: `patient/${patientId}/labs`, type: 'create' })
  }
  return created
}

export function createPatient(input: {
  name?: string
  dateOfBirth?: string
  dob?: string
  gender?: Patient['gender']
  phone?: string
  medicalRecordNo?: string
}) {
  const dateOfBirth = input.dateOfBirth || input.dob || ''
  const patient: Patient = {
    id: nextId('patient'),
    name: input.name?.trim() || 'Нэргүй өвчтөн',
    age: ageFromDob(dateOfBirth),
    gender: input.gender ?? 'other',
    medicalRecordNo: input.medicalRecordNo?.trim() || `MR-${new Date().getFullYear()}-${String(store().patients.length + 1).padStart(3, '0')}`,
    dateOfBirth,
    phone: input.phone?.trim() || undefined,
    lastVisit: todayDate(),
  }
  store().patients.unshift(patient)
  addAuditEvent({ actor: currentUser.name, action: 'Өвчтөн үүсгэсэн', entity: `patient/${patient.id}`, type: 'create' })
  return patient
}

export function listCases() {
  return store().cases
}

export function getCase(id: string) {
  return store().cases.find((clinicalCase) => clinicalCase.id === id)
}

export function createCase(input: { patientId?: string; chiefComplaint?: string }) {
  const patient = getPatient(input.patientId ?? '')
  if (!patient) return null
  const createdAt = new Date().toISOString()
  const clinicalCase: ClinicalCase = {
    id: nextId('case'),
    patientId: patient.id,
    patientName: patient.name,
    chiefComplaint: input.chiefComplaint?.trim() || 'Гол зовиур оруулаагүй',
    status: 'draft',
    createdAt,
    updatedAt: createdAt,
    hasRedFlag: false,
    symptoms: [],
    labResults: [],
    medications: [],
  }
  store().cases.unshift(clinicalCase)
  addAuditEvent({ actor: currentUser.name, action: 'Тохиолдол үүсгэсэн', entity: `case/${clinicalCase.id}`, type: 'create' })
  return clinicalCase
}

export function updateCase(id: string, patch: Partial<ClinicalCase>) {
  const data = store()
  const index = data.cases.findIndex((clinicalCase) => clinicalCase.id === id)
  if (index === -1) return null
  const next: ClinicalCase = { ...data.cases[index], ...patch, id, updatedAt: new Date().toISOString() }
  data.cases[index] = next
  addAuditEvent({ actor: currentUser.name, action: 'Тохиолдол шинэчилсэн', entity: `case/${id}`, type: 'update' })
  return next
}

export function deleteCase(id: string) {
  const data = store()
  const index = data.cases.findIndex((clinicalCase) => clinicalCase.id === id)
  if (index === -1) return null
  const [deleted] = data.cases.splice(index, 1)
  addAuditEvent({ actor: currentUser.name, action: 'Тохиолдол устгасан', entity: `case/${id}`, type: 'update' })
  return deleted
}

export function saveDoctorDecision(id: string, input: { decision?: string; finalNote?: string }) {
  const clinicalCase = updateCase(id, { status: 'doctor_reviewed' })
  if (!clinicalCase) return null
  addAuditEvent({
    actor: currentUser.name,
    action: `Doctor decision: ${input.decision ?? 'unknown'}`,
    entity: `case/${id}`,
    type: 'decision',
  })
  return { case: clinicalCase, decision: input.decision, finalNote: input.finalNote ?? '' }
}

export function dashboardSummary() {
  const data = store()
  const today = todayDate()
  const todayCases = data.cases.filter((clinicalCase) => clinicalCase.createdAt.startsWith(today))
  return {
    currentUser,
    stats: {
      todayCases: todayCases.length || data.cases.length,
      newCases: data.cases.filter((clinicalCase) => clinicalCase.status === 'draft').length,
      aiComplete: data.cases.filter((clinicalCase) => clinicalCase.status === 'ai_complete').length,
      redFlags: data.cases.filter((clinicalCase) => clinicalCase.hasRedFlag).length,
      patients: data.patients.length,
    },
    cases: data.cases,
  }
}

export function adminOverview() {
  const data = store()
  return {
    hospitals: data.hospitals,
    users: data.users,
    uploads: data.uploads,
    stats: {
      users: data.users.length,
      hospitals: data.hospitals.length,
      activeUsers: data.users.filter((user) => user.status === 'active').length,
      patients: data.patients.length,
      cases: data.cases.length,
      uploads: data.uploads.length,
      review: data.uploads.filter((upload) => upload.extractionStatus === 'requires_review').length,
      failed: data.uploads.filter((upload) => upload.extractionStatus === 'failed').length,
    },
  }
}

export function createHospital(input: { name?: string; adminName?: string; adminEmail?: string; plan?: string }) {
  const hospital: Hospital = {
    id: nextId('org'),
    name: input.name?.trim() || 'Шинэ hospital',
    adminName: input.adminName?.trim() || 'Hospital admin',
    adminEmail: input.adminEmail?.trim() || 'admin@hospital.mn',
    plan: input.plan || 'mvp',
    status: 'active',
    doctors: 0,
    patients: 0,
  }
  store().hospitals.unshift(hospital)
  addAuditEvent({ actor: 'А. Оюун (Admin)', action: 'Hospital үүсгэсэн', entity: `hospital/${hospital.id}`, type: 'admin' })
  return hospital
}

export function toggleHospital(id: string) {
  const hospital = store().hospitals.find((item) => item.id === id)
  if (!hospital) return null
  hospital.status = hospital.status === 'active' ? 'disabled' : 'active'
  addAuditEvent({ actor: 'А. Оюун (Admin)', action: `Hospital ${hospital.status}`, entity: `hospital/${id}`, type: 'admin' })
  return hospital
}

export function createAdminUser(input: { name?: string; email?: string; role?: AdminUser['role'] }) {
  const user: AdminUser = {
    id: nextId('user'),
    name: input.name?.trim() || 'Шинэ хэрэглэгч',
    email: input.email?.trim() || 'user@clinic.mn',
    role: input.role ?? 'doctor',
    status: 'active',
    lastSeen: 'Шинэ хэрэглэгч',
  }
  store().users.unshift(user)
  addAuditEvent({ actor: 'А. Оюун (Admin)', action: 'Хэрэглэгч үүсгэсэн', entity: `user/${user.id}`, type: 'admin' })
  return user
}

export function toggleAdminUser(id: string) {
  const user = store().users.find((item) => item.id === id)
  if (!user) return null
  user.status = user.status === 'active' ? 'disabled' : 'active'
  addAuditEvent({ actor: 'А. Оюун (Admin)', action: `Хэрэглэгч ${user.status}`, entity: `user/${id}`, type: 'admin' })
  return user
}

export function markUploadReviewed(id: string) {
  const upload = store().uploads.find((item) => item.id === id)
  if (!upload) return null
  upload.extractionStatus = 'processed'
  addAuditEvent({ actor: 'А. Оюун (Admin)', action: 'Upload review баталсан', entity: `upload/${id}`, type: 'admin' })
  return upload
}

export function listAuditEvents() {
  return store().auditEvents
}
