'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/layout/AppShell'
import Link from 'next/link'
import { clinicalApi } from '@/lib/clinical-api'

export default function NewPatientPage() {
  const router = useRouter()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', dob: '', gender: 'female', phone: '', medicalRecordNo: '', comorbidities: '' })

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await clinicalApi.createPatient({
        name: form.name,
        dateOfBirth: form.dob,
        gender: form.gender,
        phone: form.phone,
        medicalRecordNo: form.medicalRecordNo,
      })
      router.push('/patients')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Patient API алдаа гарлаа')
      setSaving(false)
    }
  }

  return (
    <AppShell>
      <div className="p-8 max-w-2xl">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-6">
          <Link href="/patients" className="hover:text-slate-600">Өвчтөнүүд</Link>
          <span>/</span>
          <span className="text-slate-700">Шинэ өвчтөн</span>
        </div>

        <h1 className="text-2xl font-bold text-slate-900 mb-6">Шинэ өвчтөн бүртгэх</h1>
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <form onSubmit={handleSave} className="bg-white rounded-xl border border-slate-100 shadow-sm p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Бүтэн нэр <span className="text-red-500">*</span></label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Овог нэр"
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Төрсөн огноо <span className="text-red-500">*</span></label>
              <input
                type="date"
                required
                value={form.dob}
                onChange={(e) => setForm({ ...form, dob: e.target.value })}
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Хүйс <span className="text-red-500">*</span></label>
              <select
                value={form.gender}
                onChange={(e) => setForm({ ...form, gender: e.target.value })}
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="female">Эмэгтэй</option>
                <option value="male">Эрэгтэй</option>
                <option value="other">Бусад</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Утасны дугаар</label>
              <input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="+976 9900-0000"
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Эмнэлгийн бүртгэлийн №</label>
              <input
                value={form.medicalRecordNo}
                onChange={(e) => setForm({ ...form, medicalRecordNo: e.target.value })}
                placeholder="MR-2026-..."
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Хавсарсан өвчин</label>
              <input
                value={form.comorbidities}
                onChange={(e) => setForm({ ...form, comorbidities: e.target.value })}
                placeholder="ЧЭӨ, Чихрийн шижин, Зүрхний дутагдал..."
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <Link href="/patients" className="flex-1 text-center py-2.5 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition">
              Цуцлах
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-medium py-2.5 rounded-lg text-sm transition flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Хадгалж байна...
                </>
              ) : 'Өвчтөн бүртгэх'}
            </button>
          </div>
        </form>
      </div>
    </AppShell>
  )
}
