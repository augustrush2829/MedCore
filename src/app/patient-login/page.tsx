'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { PATIENT_PROFILE_KEY, PATIENT_TOKEN_KEY, patientLogin } from '@/lib/patient-api'

export default function PatientLoginPage() {
  const router = useRouter()
  const [loginIdentifier, setLoginIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const result = await patientLogin(loginIdentifier, password)
      window.localStorage.setItem(PATIENT_TOKEN_KEY, result.access_token)
      window.localStorage.setItem(PATIENT_PROFILE_KEY, JSON.stringify(result.patient))
      router.push('/patient-portal')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Нэвтрэхэд алдаа гарлаа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="mb-6">
          <Link href="/" className="text-sm text-slate-500 hover:text-slate-800">Эмчийн нэвтрэлт рүү буцах</Link>
        </div>

        <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-7">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold">P</div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">Өвчтөний нэвтрэлт</h1>
              <p className="text-sm text-slate-500">Шинжилгээ, оношийн тайлбар авах хэсэг</p>
            </div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Өвчтөний код</label>
              <input
                value={loginIdentifier}
                onChange={(event) => setLoginIdentifier(event.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Нууц үг</label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                required
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white rounded-lg py-2.5 text-sm font-medium transition"
            >
              {loading ? 'Нэвтэрч байна...' : 'Өвчтөний database хэсэгт орох'}
            </button>
          </form>

        </section>
      </div>
    </main>
  )
}
