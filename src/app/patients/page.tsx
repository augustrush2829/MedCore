'use client'

import { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import Link from 'next/link'
import type { Patient } from '@/types'
import { clinicalApi } from '@/lib/clinical-api'

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [search, setSearch] = useState('')
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

  return (
    <AppShell>
      <div className="p-8 max-w-5xl">
        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Өвчтөнүүд</h1>
            <p className="text-slate-500 text-sm mt-0.5">Нийт {patients.length} өвчтөн</p>
          </div>
          <Link href="/patients/new" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            + Шинэ өвчтөн
          </Link>
        </div>

        <div className="relative mb-6">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">🔍</span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Нэр эсвэл дугаараар хайх..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 bg-white"
          />
        </div>

        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Өвчтөн</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Бүртгэлийн №</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Нас / Хүйс</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Сүүлд үзүүлсэн</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50 transition group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold text-sm shrink-0">{p.name.charAt(0)}</div>
                      <div>
                        <p className="font-medium text-slate-900 text-sm">{p.name}</p>
                        <p className="text-slate-400 text-xs">{p.phone}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4"><span className="font-mono text-xs text-slate-600 bg-slate-100 px-2 py-1 rounded">{p.medicalRecordNo}</span></td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-slate-700">{p.age} нас</span>
                    <span className="text-slate-400 text-xs ml-1">· {p.gender === 'male' ? 'Эр' : p.gender === 'female' ? 'Эм' : 'Бусад'}</span>
                  </td>
                  <td className="px-6 py-4"><span className="text-sm text-slate-600">{p.lastVisit ?? '—'}</span></td>
                  <td className="px-6 py-4 text-right">
                    <Link href={`/patients/${p.id}`} className="text-blue-600 hover:text-blue-700 text-sm font-medium opacity-0 group-hover:opacity-100 transition">Харах →</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && <div className="text-center py-12 text-slate-400 text-sm">Хайлтад тохирох өвчтөн олдсонгүй</div>}
        </div>
      </div>
    </AppShell>
  )
}
