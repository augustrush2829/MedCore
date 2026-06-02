'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/layout/AppShell'
import Link from 'next/link'
import { useEffect } from 'react'
import type { Patient } from '@/types'
import { clinicalApi } from '@/lib/clinical-api'

export default function NewCasePage() {
  const router = useRouter()
  const [patients, setPatients] = useState<Patient[]>([])
  const [search, setSearch] = useState('')
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null)
  const [chiefComplaint, setChiefComplaint] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    clinicalApi.patients()
      .then(setPatients)
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Patients API алдаа гарлаа'))
  }, [])

  const filtered = patients.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.medicalRecordNo.toLowerCase().includes(search.toLowerCase())
  )

  const canCreate = selectedPatient && chiefComplaint.trim().length > 0

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canCreate) return
    setCreating(true)
    setError('')
    try {
      const created = await clinicalApi.createCase({ patientId: selectedPatient, chiefComplaint })
      router.push(`/cases/${created.id}`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Case API алдаа гарлаа')
      setCreating(false)
    }
  }

  return (
    <AppShell>
      <div className="p-8 max-w-3xl">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-6">
          <Link href="/dashboard" className="hover:text-slate-600">Хяналтын самбар</Link>
          <span>/</span>
          <span className="text-slate-700">Шинэ тохиолдол</span>
        </div>

        <h1 className="text-2xl font-bold text-slate-900 mb-6">Шинэ тохиолдол үүсгэх</h1>
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <form onSubmit={handleCreate} className="space-y-6">
          {/* Step 1: Patient */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">1</span>
              <h2 className="font-semibold text-slate-900">Өвчтөн сонгох</h2>
            </div>

            <div className="relative mb-4">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">🔍</span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Нэр эсвэл дугаараар хайх..."
                className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            <div className="space-y-2 max-h-64 overflow-auto scrollbar-thin">
              {filtered.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setSelectedPatient(p.id)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition ${
                    selectedPatient === p.id
                      ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500'
                      : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold text-sm shrink-0">
                    {p.name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 text-sm">{p.name}</p>
                    <p className="text-slate-400 text-xs">{p.medicalRecordNo} · {p.age} нас · {p.gender === 'male' ? 'Эр' : 'Эм'}</p>
                  </div>
                  {selectedPatient === p.id && <span className="text-blue-600 shrink-0">✓</span>}
                </button>
              ))}
              {filtered.length === 0 && (
                <div className="text-center py-6 text-slate-400 text-sm">
                  Олдсонгүй.{' '}
                  <Link href="/patients/new" className="text-blue-600 hover:underline">Шинэ өвчтөн бүртгэх →</Link>
                </div>
              )}
            </div>
          </div>

          {/* Step 2: Chief complaint */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">2</span>
              <h2 className="font-semibold text-slate-900">Гол зовиур</h2>
            </div>
            <textarea
              value={chiefComplaint}
              onChange={(e) => setChiefComplaint(e.target.value)}
              rows={3}
              placeholder="Жишээ: Хэвлийн өвдөлт, дотор муухайрах, 3 хоногийн турш..."
              className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Link href="/dashboard" className="flex-1 text-center py-2.5 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition">
              Цуцлах
            </Link>
            <button
              type="submit"
              disabled={!canCreate || creating}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-medium py-2.5 rounded-lg text-sm transition flex items-center justify-center gap-2"
            >
              {creating ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Үүсгэж байна...
                </>
              ) : 'Тохиолдол үүсгэх →'}
            </button>
          </div>
        </form>
      </div>
    </AppShell>
  )
}
