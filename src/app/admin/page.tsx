'use client'

import { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { clinicalApi } from '@/lib/clinical-api'

type AdminUser = {
  id: string
  name: string
  email: string
  role: 'doctor' | 'pharmacist' | 'admin' | 'auditor'
  status: 'active' | 'disabled'
  lastSeen: string
}

type UploadReview = {
  id: string
  patientName: string
  patientId: string
  labName: string
  collectedAt: string
  extractionStatus: 'processed' | 'requires_review' | 'failed'
  ocrLanguages: string
  hasImage: boolean
}

type Hospital = {
  id: string
  name: string
  plan: string
  status: 'active' | 'disabled'
  adminName: string
  adminEmail: string
  doctors: number
  patients: number
}

const tabs = ['overview', 'hospitals', 'users', 'uploads', 'security'] as const
type Tab = typeof tabs[number]

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [users, setUsers] = useState<AdminUser[]>([])
  const [uploads, setUploads] = useState<UploadReview[]>([])
  const [hospitals, setHospitals] = useState<Hospital[]>([])
  const [stats, setStats] = useState({ users: 0, hospitals: 0, activeUsers: 0, patients: 0, cases: 0, uploads: 0, review: 0, failed: 0 })
  const [draft, setDraft] = useState({ name: '', email: '', role: 'doctor' as AdminUser['role'] })
  const [hospitalDraft, setHospitalDraft] = useState({ name: '', adminName: '', adminEmail: '', plan: 'mvp' })
  const [error, setError] = useState('')

  const refresh = () => {
    clinicalApi.admin()
      .then((payload) => {
        setHospitals(payload.hospitals)
        setUsers(payload.users)
        setUploads(payload.uploads)
        setStats(payload.stats)
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Admin API алдаа гарлаа'))
  }

  useEffect(() => {
    refresh()
  }, [])

  const createHospital = async () => {
    if (!hospitalDraft.name.trim() || !hospitalDraft.adminEmail.trim() || !hospitalDraft.adminName.trim()) return
    try {
      await clinicalApi.createHospital(hospitalDraft)
      setHospitalDraft({ name: '', adminName: '', adminEmail: '', plan: 'mvp' })
      refresh()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Hospital API алдаа гарлаа')
    }
  }

  const toggleHospital = async (id: string) => {
    try {
      await clinicalApi.toggleHospital(id)
      refresh()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Hospital API алдаа гарлаа')
    }
  }

  const addUser = async () => {
    if (!draft.name.trim() || !draft.email.trim()) return
    try {
      await clinicalApi.createUser(draft)
      setDraft({ name: '', email: '', role: 'doctor' })
      refresh()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'User API алдаа гарлаа')
    }
  }

  const toggleUser = async (id: string) => {
    try {
      await clinicalApi.toggleUser(id)
      refresh()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'User API алдаа гарлаа')
    }
  }

  const markReviewed = async (id: string) => {
    try {
      await clinicalApi.markUploadReviewed(id)
      refresh()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Upload API алдаа гарлаа')
    }
  }

  return (
    <AppShell>
      <div className="p-8 max-w-7xl">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Админ удирдлага</h1>
            <p className="text-slate-500 text-sm mt-1">Байгууллагын хэрэглэгч, patient portal, OCR upload, audit/security хяналт</p>
          </div>
        </div>
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <div className="flex gap-2 mb-6">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition ${activeTab === tab ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}
            >
              {tabLabel(tab)}
            </button>
          ))}
        </div>

        {activeTab === 'overview' && <Overview stats={stats} />}
        {activeTab === 'hospitals' && (
          <HospitalsPanel
            hospitals={hospitals}
            draft={hospitalDraft}
            onDraft={setHospitalDraft}
            onAdd={createHospital}
            onToggle={toggleHospital}
          />
        )}
        {activeTab === 'users' && (
          <UsersPanel
            users={users}
            draft={draft}
            onDraft={setDraft}
            onAdd={addUser}
            onToggle={toggleUser}
          />
        )}
        {activeTab === 'uploads' && <UploadsPanel uploads={uploads} onReviewed={markReviewed} />}
        {activeTab === 'security' && <SecurityPanel />}
      </div>
    </AppShell>
  )
}

function Overview({ stats }: { stats: { hospitals: number; users: number; activeUsers: number; patients: number; cases: number; uploads: number; review: number; failed: number } }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <Metric label="Hospitals" value={stats.hospitals} detail="super admin scoped" />
        <Metric label="Нийт хэрэглэгч" value={stats.users} detail={`${stats.activeUsers} active`} />
        <Metric label="Өвчтөн" value={stats.patients} detail="tenant scoped" />
        <Metric label="Clinical case" value={stats.cases} detail="AI workflow" />
      </div>
      <div className="grid grid-cols-4 gap-4">
        <Metric label="Patient uploads" value={stats.uploads} detail={`${stats.review} review, ${stats.failed} failed`} tone={stats.review || stats.failed ? 'warning' : 'default'} />
        <Metric label="OCR хэл" value={2} detail="eng + mon" />
        <Metric label="Storage" value={1} detail="encrypted object-key mode" />
        <Metric label="Audit" value={1} detail="admin actions logged" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <ControlCard title="Patient portal хяналт" items={['Зураг encrypted file storage-д хадгалагдана', 'DB-д object key/hash/metadata хадгална', 'Image endpoint patient/admin scope шалгана', 'Tesseract OCR eng+mon extraction хадгална']} />
        <ControlCard title="Admin API capability" items={['/admin/overview', '/admin/users create/update/disable', '/admin/portal-explanations list/review', '/admin/portal-explanations/{id}/image scoped access']} />
      </div>
    </div>
  )
}

function HospitalsPanel({ hospitals, draft, onDraft, onAdd, onToggle }: {
  hospitals: Hospital[]
  draft: { name: string; adminName: string; adminEmail: string; plan: string }
  onDraft: (draft: { name: string; adminName: string; adminEmail: string; plan: string }) => void
  onAdd: () => void
  onToggle: (id: string) => void
}) {
  return (
    <div className="grid grid-cols-[380px_1fr] gap-5">
      <section className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-900 mb-1">Hospital үүсгэх</h2>
        <p className="text-xs text-slate-500 mb-4">Super admin hospital үүсгээд hospital admin account хамт нээнэ.</p>
        <div className="space-y-3">
          <input value={draft.name} onChange={(event) => onDraft({ ...draft, name: event.target.value })} placeholder="Hospital нэр" className={inputClass} />
          <input value={draft.adminName} onChange={(event) => onDraft({ ...draft, adminName: event.target.value })} placeholder="Hospital admin нэр" className={inputClass} />
          <input value={draft.adminEmail} onChange={(event) => onDraft({ ...draft, adminEmail: event.target.value })} placeholder="admin@hospital.mn" className={inputClass} />
          <select value={draft.plan} onChange={(event) => onDraft({ ...draft, plan: event.target.value })} className={inputClass}>
            <option value="mvp">MVP</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>
          <button onClick={onAdd} className="w-full rounded-lg bg-slate-900 text-white py-2.5 text-sm font-medium hover:bg-slate-800">Hospital + admin үүсгэх</button>
        </div>
      </section>
      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th className="text-left px-4 py-3">Hospital</th>
              <th className="text-left px-4 py-3">Admin</th>
              <th className="text-left px-4 py-3">Plan</th>
              <th className="text-left px-4 py-3">Usage</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {hospitals.map((hospital) => (
              <tr key={hospital.id}>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-900">{hospital.name}</div>
                  <div className="text-xs text-slate-500">{hospital.id}</div>
                </td>
                <td className="px-4 py-3">
                  <div className="text-slate-900">{hospital.adminName}</div>
                  <div className="text-xs text-slate-500">{hospital.adminEmail}</div>
                </td>
                <td className="px-4 py-3 text-slate-600">{hospital.plan}</td>
                <td className="px-4 py-3 text-slate-600">{hospital.doctors} doctors · {hospital.patients} patients</td>
                <td className="px-4 py-3"><StatusBadge value={hospital.status} /></td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => onToggle(hospital.id)} className="text-xs text-blue-600 hover:underline">
                    {hospital.status === 'active' ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}

function UsersPanel({ users, draft, onDraft, onAdd, onToggle }: {
  users: AdminUser[]
  draft: { name: string; email: string; role: AdminUser['role'] }
  onDraft: (draft: { name: string; email: string; role: AdminUser['role'] }) => void
  onAdd: () => void
  onToggle: (id: string) => void
}) {
  return (
    <div className="grid grid-cols-[360px_1fr] gap-5">
      <section className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-900 mb-4">Хэрэглэгч нэмэх</h2>
        <div className="space-y-3">
          <input value={draft.name} onChange={(event) => onDraft({ ...draft, name: event.target.value })} placeholder="Нэр" className={inputClass} />
          <input value={draft.email} onChange={(event) => onDraft({ ...draft, email: event.target.value })} placeholder="email@clinic.mn" className={inputClass} />
          <select value={draft.role} onChange={(event) => onDraft({ ...draft, role: event.target.value as AdminUser['role'] })} className={inputClass}>
            <option value="doctor">Doctor</option>
            <option value="pharmacist">Pharmacist</option>
            <option value="admin">Admin</option>
            <option value="auditor">Auditor</option>
          </select>
          <button onClick={onAdd} className="w-full rounded-lg bg-blue-600 text-white py-2.5 text-sm font-medium hover:bg-blue-700">Нэмэх</button>
        </div>
      </section>
      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th className="text-left px-4 py-3">Нэр</th>
              <th className="text-left px-4 py-3">Role</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Last seen</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.map((user) => (
              <tr key={user.id}>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-900">{user.name}</div>
                  <div className="text-xs text-slate-500">{user.email}</div>
                </td>
                <td className="px-4 py-3 text-slate-600">{user.role}</td>
                <td className="px-4 py-3"><StatusBadge value={user.status} /></td>
                <td className="px-4 py-3 text-slate-500">{user.lastSeen}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => onToggle(user.id)} className="text-xs text-blue-600 hover:underline">
                    {user.status === 'active' ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}

function UploadsPanel({ uploads, onReviewed }: { uploads: UploadReview[]; onReviewed: (id: string) => void }) {
  return (
    <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs text-slate-500">
          <tr>
            <th className="text-left px-4 py-3">Patient</th>
            <th className="text-left px-4 py-3">Lab</th>
            <th className="text-left px-4 py-3">OCR</th>
            <th className="text-left px-4 py-3">Status</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {uploads.map((upload) => (
            <tr key={upload.id}>
              <td className="px-4 py-3">
                <div className="font-medium text-slate-900">{upload.patientName}</div>
                <div className="text-xs text-slate-500">patient_id: {upload.patientId}</div>
              </td>
              <td className="px-4 py-3">
                <div className="text-slate-900">{upload.labName}</div>
                <div className="text-xs text-slate-500">{upload.collectedAt}</div>
              </td>
              <td className="px-4 py-3 text-slate-600">{upload.ocrLanguages}</td>
              <td className="px-4 py-3"><ExtractionBadge value={upload.extractionStatus} /></td>
              <td className="px-4 py-3 text-right">
                {upload.extractionStatus !== 'processed' && (
                  <button onClick={() => onReviewed(upload.id)} className="text-xs text-blue-600 hover:underline">Mark reviewed</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function SecurityPanel() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <ControlCard title="Access control" items={['Admin endpoints require user:manage/admin:* permissions', 'Portal image access checks organization_id + patient_id', 'Admin image access checks organization_id', 'Object key is not returned to patient frontend']} />
      <ControlCard title="Storage controls" items={['Images encrypted before local file write', 'DB stores hash, size, dimensions, content type', 'Path traversal guard blocks ../ object keys', 'Upload directories are gitignored']} />
      <ControlCard title="Audit controls" items={['Admin user create/update writes audit', 'Admin image view writes audit', 'Patient portal records keep created_at and lab_collected_at', 'OCR raw text is retained for review']} />
      <ControlCard title="Operational gaps" items={['Add Alembic migrations before production', 'Move local storage to S3/GCS with KMS', 'Add MFA/OTP for patient login', 'Add retention and deletion workflow']} />
    </div>
  )
}

function Metric({ label, value, detail, tone = 'default' }: { label: string; value: number; detail: string; tone?: 'default' | 'warning' }) {
  return (
    <div className={`rounded-xl border p-5 bg-white ${tone === 'warning' ? 'border-amber-200' : 'border-slate-200'}`}>
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="text-3xl font-bold text-slate-900 mt-2">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{detail}</p>
    </div>
  )
}

function ControlCard({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5">
      <h2 className="font-semibold text-slate-900 mb-3">{title}</h2>
      <ul className="space-y-2">
        {items.map((item) => <li key={item} className="text-sm text-slate-600">{item}</li>)}
      </ul>
    </section>
  )
}

function StatusBadge({ value }: { value: AdminUser['status'] }) {
  return <span className={`text-xs px-2 py-1 rounded-full font-medium ${value === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>{value}</span>
}

function ExtractionBadge({ value }: { value: UploadReview['extractionStatus'] }) {
  const style = value === 'processed' ? 'bg-green-100 text-green-700' : value === 'requires_review' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'
  return <span className={`text-xs px-2 py-1 rounded-full font-medium ${style}`}>{value}</span>
}

function tabLabel(tab: Tab) {
  return tab === 'overview' ? 'Ерөнхий' : tab === 'hospitals' ? 'Hospitals' : tab === 'users' ? 'Хэрэглэгчид' : tab === 'uploads' ? 'Patient uploads' : 'Security'
}

const inputClass = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'
