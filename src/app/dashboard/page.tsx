'use client'

import { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import Link from 'next/link'
import { clinicalApi, type DashboardPayload } from '@/lib/clinical-api'

const statusLabel: Record<string, { label: string; color: string }> = {
  draft: { label: 'Ноорог', color: 'bg-slate-100 text-slate-600' },
  ai_pending: { label: 'AI шинжилж байна', color: 'bg-amber-100 text-amber-700' },
  ai_complete: { label: 'AI бэлэн', color: 'bg-blue-100 text-blue-700' },
  doctor_reviewed: { label: 'Шалгасан', color: 'bg-green-100 text-green-700' },
  finalized: { label: 'Дууссан', color: 'bg-slate-100 text-slate-500' },
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    clinicalApi.dashboard()
      .then(setData)
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Dashboard API алдаа гарлаа'))
  }, [])

  const today = new Date().toLocaleDateString('mn-MN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
  const stats = data ? [
    { label: 'Өнөөдрийн тохиолдол', value: String(data.stats.todayCases), sub: `${data.stats.newCases} шинэ`, color: 'text-blue-600' },
    { label: 'AI бэлэн', value: String(data.stats.aiComplete), sub: 'Шийдвэр хүлээж байна', color: 'text-indigo-600' },
    { label: 'Улаан дохио', value: String(data.stats.redFlags), sub: 'Яаралтай', color: 'text-red-600' },
    { label: 'Нийт өвчтөн', value: String(data.stats.patients), sub: 'Байгууллагадаа', color: 'text-slate-700' },
  ] : []

  return (
    <AppShell>
      <div className="p-8 max-w-7xl">
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        {!data ? (
          <div className="text-sm text-slate-500">Dashboard API-аас уншиж байна...</div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Сайн байна уу, {data.currentUser.name}</h1>
                <p className="text-slate-500 text-sm mt-0.5">{today}</p>
              </div>
              <Link href="/cases/new" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2">
                + Шинэ тохиолдол
              </Link>
            </div>

            <div className="grid grid-cols-4 gap-4 mb-8">
              {stats.map((s) => (
                <div key={s.label} className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
                  <p className="text-slate-500 text-xs font-medium">{s.label}</p>
                  <p className={`text-3xl font-bold mt-1 ${s.color}`}>{s.value}</p>
                  <p className="text-slate-400 text-xs mt-1">{s.sub}</p>
                </div>
              ))}
            </div>

            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-5 mb-8 flex items-center justify-between text-white">
              <div>
                <p className="font-semibold">AI Clinical Support бэлэн байна</p>
                <p className="text-blue-200 text-sm mt-0.5">{data.stats.aiComplete} тохиолдлын шинжилгээ дуусч, таны шийдвэр хүлээж байна</p>
              </div>
              <Link href="/cases/c1/ai-result" className="bg-white text-blue-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-50 transition shrink-0">
                Харах →
              </Link>
            </div>

            <div className="bg-white rounded-xl border border-slate-100 shadow-sm">
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                <h2 className="font-semibold text-slate-900">Өнөөдрийн тохиолдлууд</h2>
                <Link href="/cases" className="text-blue-600 text-sm hover:underline">Бүгдийг харах</Link>
              </div>
              <div className="divide-y divide-slate-50">
                {data.cases.map((c) => {
                  const st = statusLabel[c.status]
                  return (
                    <Link key={c.id} href={c.status === 'ai_complete' ? `/cases/${c.id}/ai-result` : `/cases/${c.id}`} className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50 transition group">
                      <div className="w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-semibold text-sm shrink-0">{c.patientName.charAt(0)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-900 text-sm">{c.patientName}</span>
                          {c.hasRedFlag && <span className="bg-red-100 text-red-600 text-xs px-1.5 py-0.5 rounded font-medium">🚨 Улаан дохио</span>}
                        </div>
                        <p className="text-slate-500 text-xs mt-0.5 truncate">{c.chiefComplaint}</p>
                      </div>
                      <span className={`text-xs px-2.5 py-1 rounded-full font-medium shrink-0 ${st.color}`}>{st.label}</span>
                      <span className="text-slate-400 text-xs shrink-0">{new Date(c.createdAt).toLocaleTimeString('mn-MN', { hour: '2-digit', minute: '2-digit' })}</span>
                      <span className="text-slate-300 group-hover:text-slate-500 transition">→</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  )
}
