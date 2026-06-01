'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  PATIENT_PROFILE_KEY,
  PATIENT_TOKEN_KEY,
  createPatientExplanation,
  fetchPatientExplanationImage,
  fetchPatientExplanations,
  type PatientExplanation,
  type PatientPortalUser,
} from '@/lib/patient-api'

const inputClass = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20'

export default function PatientPortalPage() {
  const router = useRouter()
  const [token] = useState(() => (typeof window === 'undefined' ? '' : window.localStorage.getItem(PATIENT_TOKEN_KEY) ?? ''))
  const [patient] = useState<PatientPortalUser | null>(() => {
    if (typeof window === 'undefined') return null
    const storedProfile = window.localStorage.getItem(PATIENT_PROFILE_KEY)
    return storedProfile ? JSON.parse(storedProfile) as PatientPortalUser : null
  })
  const [items, setItems] = useState<PatientExplanation[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [selectedImage, setSelectedImage] = useState<{ explanationId: string; url: string } | null>(null)
  const [form, setForm] = useState({
    diagnosis_text: 'Элэгний фермент өссөн',
    lab_name: 'ALT',
    lab_value: '120',
    lab_unit: 'U/L',
    reference_range: '7-40',
    lab_collected_at: new Date().toISOString().slice(0, 10),
    patient_question: 'Энэ хариу аюултай юу?',
    attachment_name: '',
    attachment_content_type: '',
    attachment_data_url: '',
  })

  useEffect(() => {
    if (!token || !patient) {
      router.push('/patient-login')
      return
    }
    fetchPatientExplanations(token)
      .then((result) => {
        setItems(result)
        setSelectedId(result[0]?.id ?? null)
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Database-аас уншихад алдаа гарлаа'))
      .finally(() => setLoading(false))
  }, [patient, router, token])

  const selected = useMemo(
    () => items.find((item) => item.id === selectedId) ?? items[0] ?? null,
    [items, selectedId],
  )

  useEffect(() => {
    if (!selected?.has_attachment || !token) {
      return
    }
    let active = true
    let objectUrl: string | null = null
    fetchPatientExplanationImage(token, selected.id)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setSelectedImage({ explanationId: selected.id, url: objectUrl })
      })
      .catch(() => undefined)
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [selected?.has_attachment, selected?.id, token])

  const handleImage = (file: File | null) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Зөвхөн зураг файл оруулна уу')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      setForm((current) => ({
        ...current,
        attachment_name: file.name,
        attachment_content_type: file.type,
        attachment_data_url: String(reader.result),
      }))
    }
    reader.readAsDataURL(file)
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!token) return
    setSaving(true)
    setError('')
    try {
      const created = await createPatientExplanation(token, {
        diagnosis_text: form.diagnosis_text || null,
        lab_name: form.lab_name || null,
        lab_value: form.lab_value || null,
        lab_unit: form.lab_unit || null,
        reference_range: form.reference_range || null,
        lab_collected_at: form.lab_collected_at || null,
        attachment_name: form.attachment_name || null,
        attachment_content_type: form.attachment_content_type || null,
        attachment_data_url: form.attachment_data_url || null,
        patient_question: form.patient_question || null,
      })
      setItems((current) => [created, ...current])
      setSelectedId(created.id)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Хадгалахад алдаа гарлаа')
    } finally {
      setSaving(false)
    }
  }

  const logout = () => {
    window.localStorage.removeItem(PATIENT_TOKEN_KEY)
    window.localStorage.removeItem(PATIENT_PROFILE_KEY)
    router.push('/patient-login')
  }

  if (loading) return <main className="min-h-screen bg-slate-50 p-8 text-slate-500">Уншиж байна...</main>

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-5 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-slate-900">MedCore өвчтөний хэсэг</h1>
            <p className="text-xs text-slate-500">
              {patient?.name} · {patient?.medical_record_no} · patient_id: {patient?.id}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/" className="text-sm text-slate-500 hover:text-slate-800">Эмчийн хэсэг</Link>
            <button onClick={logout} className="text-sm text-red-600 hover:text-red-700">Гарах</button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-5 py-6 grid grid-cols-[1.1fr_0.9fr] gap-6">
        <section className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-900 mb-1">Шинжилгээ, онош тайлбарлуулах</h2>
          <p className="text-sm text-slate-500 mb-5">Зураг preview харагдаад submit хийхэд backend AI extractor боловсруулж, гарсан structured data database-д хадгалагдана.</p>

          <form onSubmit={submit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Онош / эмчийн хэлсэн дүгнэлт">
                <input value={form.diagnosis_text} onChange={(event) => setForm({ ...form, diagnosis_text: event.target.value })} className={inputClass} />
              </Field>
              <Field label="Шинжилгээ авсан огноо">
                <input type="date" value={form.lab_collected_at} onChange={(event) => setForm({ ...form, lab_collected_at: event.target.value })} className={inputClass} />
              </Field>
              <Field label="Шинжилгээний нэр">
                <input value={form.lab_name} onChange={(event) => setForm({ ...form, lab_name: event.target.value })} placeholder="ALT, AST, HbA1c..." className={inputClass} />
              </Field>
              <Field label="Үр дүн">
                <div className="grid grid-cols-[1fr_0.7fr] gap-2">
                  <input value={form.lab_value} onChange={(event) => setForm({ ...form, lab_value: event.target.value })} className={inputClass} />
                  <input value={form.lab_unit} onChange={(event) => setForm({ ...form, lab_unit: event.target.value })} placeholder="U/L" className={inputClass} />
                </div>
              </Field>
              <Field label="Хэвийн хэмжээ">
                <input value={form.reference_range} onChange={(event) => setForm({ ...form, reference_range: event.target.value })} placeholder="7-40" className={inputClass} />
              </Field>
              <Field label="Шинжилгээний зураг">
                <input type="file" accept="image/*" onChange={(event) => handleImage(event.target.files?.[0] ?? null)} className="w-full text-sm text-slate-600" />
              </Field>
            </div>

            {form.attachment_data_url && (
              <div className="rounded-lg border border-slate-200 overflow-hidden bg-slate-50">
                <div className="px-3 py-2 text-xs text-slate-500 border-b border-slate-200">
                  Preview: {form.attachment_name}
                </div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={form.attachment_data_url} alt="Шинжилгээний зураг preview" className="max-h-72 w-full object-contain bg-white" />
              </div>
            )}

            <Field label="Өөрийн асуулт">
              <textarea
                value={form.patient_question}
                onChange={(event) => setForm({ ...form, patient_question: event.target.value })}
                rows={3}
                className={`${inputClass} resize-none`}
              />
            </Field>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <button disabled={saving} className="w-full rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white py-2.5 text-sm font-medium">
              {saving ? 'AI боловсруулж database-д хадгалж байна...' : 'Зургийг AI-аар боловсруулж хадгалах'}
            </button>
          </form>
        </section>

        <section className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Өмнөх хадгалсан тайлбарууд</h2>
            <div className="space-y-2 max-h-72 overflow-auto">
              {items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={`w-full text-left rounded-lg border px-3 py-2 text-sm ${selected?.id === item.id ? 'border-emerald-500 bg-emerald-50' : 'border-slate-200 hover:bg-slate-50'}`}
                >
                  <div className="font-medium text-slate-900">{item.lab_name || item.diagnosis_text || 'Тайлбар'}</div>
                  <div className="text-xs text-slate-500">
                    Шинжилгээ: {item.lab_collected_at || 'огноо байхгүй'} · Хадгалсан: {new Date(item.created_at).toLocaleString('mn-MN')}
                  </div>
                </button>
              ))}
              {items.length === 0 && <p className="text-sm text-slate-500">Одоогоор хадгалсан тайлбар байхгүй.</p>}
            </div>
          </div>

          {selected && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <h2 className="font-semibold text-slate-900">Энгийн тайлбар</h2>
                  <p className="text-xs text-slate-500">patient_id: {selected.patient_id}</p>
                </div>
                <span className="text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700">{selected.safety_status}</span>
              </div>
              {selectedImage?.explanationId === selected.id && (
                <div className="mb-4 rounded-lg border border-slate-200 overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={selectedImage.url} alt="Хадгалсан шинжилгээний зураг" className="max-h-56 w-full object-contain bg-white" />
                </div>
              )}
              <div className="mb-4 rounded-lg border border-emerald-100 bg-emerald-50 p-3">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <h3 className="text-sm font-semibold text-emerald-900">Зургаас гарсан AI дата</h3>
                  <span className="text-xs text-emerald-700">{selected.extraction_status}</span>
                </div>
                <p className="text-xs text-emerald-800 mb-2">
                  Model: {selected.extraction_model || selected.extracted_lab_data.model}
                  {selected.extracted_lab_data.ocr_engine ? ` · OCR ${selected.extracted_lab_data.ocr_engine} ${selected.extracted_lab_data.ocr_languages || ''}` : ''}
                  {selected.attachment_sha256 ? ` · sha256 ${selected.attachment_sha256.slice(0, 12)}...` : ''}
                  {selected.extracted_lab_data.image_width && selected.extracted_lab_data.image_height
                    ? ` · ${selected.extracted_lab_data.image_width}x${selected.extracted_lab_data.image_height}`
                    : ''}
                </p>
                {selected.extracted_lab_data.observations.length > 0 ? (
                  <div className="overflow-hidden rounded-md border border-emerald-200 bg-white">
                    <table className="w-full text-xs">
                      <thead className="bg-emerald-50 text-emerald-900">
                        <tr>
                          <th className="text-left px-2 py-1.5">Шинжилгээ</th>
                          <th className="text-left px-2 py-1.5">Утга</th>
                          <th className="text-left px-2 py-1.5">Хэвийн хэмжээ</th>
                          <th className="text-left px-2 py-1.5">Итгэлцэл</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selected.extracted_lab_data.observations.map((observation) => (
                          <tr key={`${observation.test_name}-${observation.value}`} className="border-t border-emerald-100">
                            <td className="px-2 py-1.5 font-medium text-slate-900">{observation.test_name}</td>
                            <td className="px-2 py-1.5 text-slate-700">
                              {observation.value || '-'} {observation.unit || ''}
                              {observation.abnormal_flag && <span className="ml-1 text-red-600">хэвийн бус</span>}
                            </td>
                            <td className="px-2 py-1.5 text-slate-600">{observation.reference_range || '-'}</td>
                            <td className="px-2 py-1.5 text-slate-600">{observation.confidence}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-emerald-800">Зургаас баталгаатай lab мөр гаргаагүй. Review шаардлагатай.</p>
                )}
                {selected.extracted_lab_data.notes.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {selected.extracted_lab_data.notes.map((note) => (
                      <li key={note} className="text-xs text-emerald-800">{note}</li>
                    ))}
                  </ul>
                )}
                {selected.extracted_lab_data.ocr_text && (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-medium text-emerald-900">OCR raw text харах</summary>
                    <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-md bg-white p-2 text-xs text-slate-700 border border-emerald-100">
                      {selected.extracted_lab_data.ocr_text}
                    </pre>
                  </details>
                )}
              </div>
              <ExplanationBlock title="Хураангуй" lines={[selected.content.summary, selected.content.lab_meaning]} />
              <ExplanationBlock title="Ойлгомжтой тайлбар" lines={selected.content.plain_language} />
              <ExplanationBlock title="Эмчээс асуух зүйлс" lines={selected.content.next_questions} />
              <ExplanationBlock title="Анхаарах шинж" lines={selected.content.safety_notes} tone="warning" />
              <p className="mt-4 text-xs text-slate-500">{selected.content.disclaimer}</p>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate-600 mb-1.5">{label}</span>
      {children}
    </label>
  )
}

function ExplanationBlock({ title, lines, tone = 'default' }: { title: string; lines: string[]; tone?: 'default' | 'warning' }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-semibold text-slate-900 mb-2">{title}</h3>
      <ul className="space-y-1.5">
        {lines.map((line) => (
          <li key={line} className={`text-sm leading-relaxed ${tone === 'warning' ? 'text-red-700' : 'text-slate-700'}`}>
            {line}
          </li>
        ))}
      </ul>
    </div>
  )
}
