'use client'

import { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import Link from 'next/link'
import type { ClinicalCase } from '@/types'
import { clinicalApi } from '@/lib/clinical-api'

const statusConfig: Record<string, { label: string; color: string }> = {
  draft: { label: 'Ноорог', color: 'bg-slate-100 text-slate-600' },
  ai_pending: { label: 'AI шинжилж байна', color: 'bg-amber-100 text-amber-700' },
  ai_complete: { label: 'AI бэлэн', color: 'bg-blue-100 text-blue-700' },
  doctor_reviewed: { label: 'Шалгасан', color: 'bg-green-100 text-green-700' },
  finalized: { label: 'Дууссан', color: 'bg-slate-100 text-slate-500' },
}

export default function CasesPage() {
  const [cases, setCases] = useState<ClinicalCase[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    clinicalApi.cases()
      .then(setCases)
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Cases API алдаа гарлаа'))
  }, [])

  return (
    <AppShell>
      <div className="p-8 max-w-4xl">
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Тохиолдлууд</h1>
            <p className="text-slate-500 text-sm mt-0.5">Нийт {cases.length} тохиолдол</p>
          </div>
          <Link href="/cases/new" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
            + Шинэ тохиолдол
          </Link>
        </div>

        <div className="space-y-3">
          {cases.map((c) => {
            const st = statusConfig[c.status]
            const href = c.status === 'ai_complete' ? `/cases/${c.id}/ai-result` : `/cases/${c.id}`
            return (
              <Link key={c.id} href={href} className="flex items-center gap-4 bg-white rounded-xl border border-slate-100 p-5 hover:border-blue-200 hover:shadow-sm transition group">
                <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 font-bold shrink-0">{c.patientName.charAt(0)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-semibold text-slate-900">{c.patientName}</span>
                    {c.hasRedFlag && <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded font-medium">🚨 Яаралтай</span>}
                  </div>
                  <p className="text-slate-500 text-sm truncate">{c.chiefComplaint}</p>
                  <p className="text-slate-400 text-xs mt-1">
                    {new Date(c.createdAt).toLocaleString('mn-MN')} ·
                    {c.symptoms.length > 0 && ` ${c.symptoms.length} симптом ·`}
                    {c.labResults.length > 0 && ` ${c.labResults.length} лаб ·`}
                    {c.medications.length > 0 && ` ${c.medications.length} эм`}
                  </p>
                </div>
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium shrink-0 ${st.color}`}>{st.label}</span>
                <span className="text-slate-300 group-hover:text-slate-500 transition shrink-0">→</span>
              </Link>
            )
          })}
        </div>
      </div>
    </AppShell>
  )
}
