'use client'
import Link from 'next/link'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setTimeout(() => router.push('/dashboard'), 800)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-500 mb-4 shadow-lg">
            <span className="text-white text-2xl font-bold">M</span>
          </div>
          <h1 className="text-white text-2xl font-bold">MedCore</h1>
          <p className="text-blue-300 text-sm mt-1">AI Clinical Decision Support</p>
        </div>

        <div className="bg-white rounded-2xl p-8 shadow-2xl">
          <h2 className="text-slate-900 text-lg font-semibold mb-1">Нэвтрэх</h2>
          <p className="text-slate-500 text-sm mb-6">Байгууллагын бүртгэлээр нэвтэрнэ үү</p>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-slate-700 text-xs font-medium mb-1.5">И-мэйл хаяг</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-slate-900 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition"
                required
              />
            </div>
            <div>
              <label className="block text-slate-700 text-xs font-medium mb-1.5">Нууц үг</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-slate-900 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-medium py-2.5 rounded-lg text-sm transition-colors flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Нэвтэрч байна...
                </>
              ) : 'Нэвтрэх'}
            </button>
          </form>

          <div className="mt-3 p-3 bg-emerald-50 border border-emerald-100 rounded-lg">
            <p className="text-emerald-700 text-xs font-medium mb-1">Өвчтөнд зориулсан хэсэг</p>
            <Link href="/patient-login" className="text-xs text-emerald-700 hover:underline">
              Шинжилгээ, оношийн тайлбар авах
            </Link>
          </div>
        </div>

        <p className="text-center text-slate-500 text-xs mt-6">
          © 2026 MedCore · Монгол Улс · Эрүүл мэндийн AI систем
        </p>
      </div>
    </div>
  )
}
