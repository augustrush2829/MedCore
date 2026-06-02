'use client'
import { use, useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import Link from 'next/link'
import type { ClinicalCase } from '@/types'
import { clinicalApi } from '@/lib/clinical-api'

const severityColor = { low: 'bg-yellow-50 border-yellow-200 text-yellow-800', medium: 'bg-orange-50 border-orange-200 text-orange-800', high: 'bg-red-50 border-red-200 text-red-800', critical: 'bg-red-100 border-red-400 text-red-900' }
const causalityLabel = { disease_related: { label: 'Өвчний явцтай холбоотой', color: 'bg-blue-100 text-blue-700' }, medication_related: { label: 'Эмийн нөлөөтэй холбоотой', color: 'bg-amber-100 text-amber-700' }, unclear: { label: 'Тодорхойгүй', color: 'bg-slate-100 text-slate-600' } }

export default function AIResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [caseData, setCaseData] = useState<ClinicalCase | null>(null)
  const [decision, setDecision] = useState<'accept' | 'edit' | 'reject' | null>(null)
  const [finalNote, setFinalNote] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    clinicalApi.case(id)
      .then(setCaseData)
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Case API алдаа гарлаа'))
  }, [id])

  if (error) {
    return <AppShell><div className="p-8 text-center text-red-600 text-sm">{error}</div></AppShell>
  }

  if (!caseData) {
    return <AppShell><div className="p-8 text-center text-slate-500">Case API-аас уншиж байна...</div></AppShell>
  }

  const ai = caseData.aiResponse

  if (!ai) {
    return (
      <AppShell>
        <div className="p-8 text-center text-slate-500">AI шинжилгээ байхгүй байна</div>
      </AppShell>
    )
  }

  const handleSubmit = async () => {
    if (!decision) return
    setError('')
    try {
      await clinicalApi.saveDecision(id, { decision, finalNote })
      setSubmitted(true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Decision API алдаа гарлаа')
    }
  }

  return (
    <AppShell>
      <div className="p-8 max-w-5xl">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-4">
          <Link href="/dashboard" className="hover:text-slate-600">Хяналтын самбар</Link>
          <span>/</span>
          <Link href={`/cases/${id}`} className="hover:text-slate-600">{caseData.patientName}</Link>
          <span>/</span>
          <span className="text-slate-700">AI Шинжилгээ</span>
        </div>

        {/* Safety disclaimer - always visible */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-3 mb-6 flex items-center gap-3">
          <span className="text-amber-600 text-lg shrink-0">⚠️</span>
          <p className="text-amber-800 text-sm font-medium">
            Энэхүү AI шинжилгээ нь эмчийн шийдвэрийг орлохгүй. Эцсийн онош, эмчилгээний шийдвэрийг эмч баталгаажуулах шаардлагатай.
          </p>
        </div>

        <ClinicalInputReview caseData={caseData} />

        {/* Red flags */}
        {ai.redFlags.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-red-600 text-lg">🚨</span>
              <h3 className="font-semibold text-red-800">Яаралтай анхааруулга</h3>
            </div>
            <ul className="space-y-1.5">
              {ai.redFlags.map((flag, i) => (
                <li key={i} className="text-red-700 text-sm flex items-start gap-2">
                  <span className="shrink-0 mt-0.5">•</span> {flag}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Medication warnings */}
        {ai.medicationWarnings.length > 0 && (
          <div className="mb-6 space-y-2">
            {ai.medicationWarnings.map((w, i) => (
              <div key={i} className={`border rounded-xl px-5 py-3 flex items-start gap-3 ${severityColor[w.severity]}`}>
                <span className="text-lg shrink-0">💊</span>
                <div>
                  <span className="font-semibold text-sm">{w.severity === 'critical' ? 'Критик' : w.severity === 'high' ? 'Өндөр эрсдэл' : 'Анхааруулга'}:</span>
                  <span className="text-sm ml-1">{w.description}</span>
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {w.medications.map((m) => (
                      <span key={m} className="text-xs bg-white/60 px-2 py-0.5 rounded border border-current/20">{m}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Header info row */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-slate-100 p-4">
            <p className="text-xs text-slate-500 font-medium">Ерөнхий итгэлцэл</p>
            <div className="flex items-center gap-3 mt-2">
              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${ai.confidenceLevel}%` }} />
              </div>
              <span className="text-lg font-bold text-slate-900">{ai.confidenceLevel}%</span>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-4">
            <p className="text-xs text-slate-500 font-medium">Шалтгааны үнэлгээ</p>
            <div className="mt-2">
              <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${causalityLabel[ai.causalityAssessment.type].color}`}>
                {causalityLabel[ai.causalityAssessment.type].label}
              </span>
              <p className="text-xs text-slate-500 mt-1">Итгэлцэл: {ai.causalityAssessment.confidence}%</p>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-4">
            <p className="text-xs text-slate-500 font-medium">Эх сурвалж</p>
            <p className="text-2xl font-bold text-slate-900 mt-2">{ai.citations.length}</p>
            <p className="text-xs text-slate-400">баримт бичиг</p>
          </div>
        </div>

        {/* Clinical summary */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6 mb-5">
          <h3 className="font-semibold text-slate-900 mb-3">Клиникийн хураангуй</h3>
          <p className="text-slate-700 text-sm leading-relaxed">{ai.clinicalSummary}</p>
        </div>

        {/* Differential diagnosis */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6 mb-5">
          <h3 className="font-semibold text-slate-900 mb-4">Ялган оношлогоо</h3>
          <div className="space-y-4">
            {ai.differentialDiagnosis.map((d, i) => (
              <div key={i} className="border border-slate-100 rounded-xl p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                      <h4 className="font-semibold text-slate-900 text-sm">{d.name}</h4>
                    </div>
                    {d.icdCode && <span className="text-xs text-slate-400 ml-8">ICD-11: {d.icdCode}</span>}
                  </div>
                  <div className="text-right shrink-0">
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${d.confidence >= 60 ? 'bg-blue-500' : d.confidence >= 40 ? 'bg-amber-500' : 'bg-slate-400'}`}
                          style={{ width: `${d.confidence}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-slate-700">{d.confidence}%</span>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 ml-8">
                  <div>
                    <p className="text-xs font-medium text-green-700 mb-1.5">✓ Дэмжих нотолгоо</p>
                    <ul className="space-y-1">
                      {d.supportingEvidence.map((e, j) => (
                        <li key={j} className="text-xs text-slate-600 flex items-start gap-1">
                          <span className="text-green-500 shrink-0">+</span> {e}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1.5">✗ Дутуу / Эсэргүүцэх</p>
                    <ul className="space-y-1">
                      {d.missingEvidence.map((e, j) => (
                        <li key={j} className="text-xs text-slate-500 flex items-start gap-1">
                          <span className="shrink-0">−</span> {e}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Missing info & recommended tests */}
        <div className="grid grid-cols-2 gap-5 mb-5">
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <h3 className="font-semibold text-slate-900 mb-3">Дутуу мэдээлэл</h3>
            <ul className="space-y-2">
              {ai.missingInformation.map((m, i) => (
                <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                  <span className="text-amber-500 shrink-0 mt-0.5">⚠</span> {m}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <h3 className="font-semibold text-slate-900 mb-3">Санал болгох шинжилгээ</h3>
            <ul className="space-y-2">
              {ai.recommendedTests.map((t, i) => (
                <li key={i} className="text-sm">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${t.priority === 'urgent' ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-500'}`}>
                      {t.priority === 'urgent' ? 'Яаралтай' : 'Энгийн'}
                    </span>
                    <span className="font-medium text-slate-900">{t.name}</span>
                  </div>
                  <p className="text-slate-500 text-xs mt-0.5 ml-14">{t.reason}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Causality */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 mb-5">
          <h3 className="font-semibold text-slate-900 mb-3">Шалтгааны үнэлгээ</h3>
          <p className="text-sm text-slate-700 leading-relaxed">{ai.causalityAssessment.evidence}</p>
        </div>

        {/* Citations */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 mb-6">
          <h3 className="font-semibold text-slate-900 mb-3">Эх сурвалж</h3>
          <div className="space-y-2">
            {ai.citations.map((c, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span className="text-slate-400 font-mono text-xs mt-0.5 shrink-0">[{i + 1}]</span>
                <div>
                  <p className="text-slate-900 font-medium text-xs">{c.title}</p>
                  <p className="text-slate-400 text-xs">{c.source} · {c.version}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Doctor decision */}
        {!submitted ? (
          <div className="bg-white rounded-xl border-2 border-blue-100 shadow-sm p-6">
            <h3 className="font-semibold text-slate-900 mb-1">Эмчийн шийдвэр</h3>
            <p className="text-slate-500 text-sm mb-5">AI-ийн шинжилгээ дээр шийдвэрээ тэмдэглэнэ үү</p>

            <div className="flex gap-3 mb-5">
              {(['accept', 'edit', 'reject'] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDecision(d)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-medium border-2 transition ${
                    decision === d
                      ? d === 'accept' ? 'bg-green-600 border-green-600 text-white'
                        : d === 'edit' ? 'bg-blue-600 border-blue-600 text-white'
                        : 'bg-red-600 border-red-600 text-white'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  {d === 'accept' ? '✓ Зөвшөөрөх' : d === 'edit' ? '✏ Засах' : '✗ Татгалзах'}
                </button>
              ))}
            </div>

            <div className="mb-5">
              <label className="block text-xs font-medium text-slate-500 mb-1.5">Эмчийн дүгнэлт ба эмчилгээний төлөвлөгөө</label>
              <textarea
                value={finalNote}
                onChange={(e) => setFinalNote(e.target.value)}
                rows={4}
                placeholder="Эцсийн онош, эмчилгээний чиглэл, дараагийн алхам..."
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
              />
            </div>

            {decision === 'edit' && (
              <Link href={`/cases/${id}`} className="mb-4 block rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700 hover:bg-blue-100">
                Оруулсан симптом, амин үзүүлэлт, лаборатори, эм, харшил болон зураг засах →
              </Link>
            )}

            <button
              onClick={handleSubmit}
              disabled={!decision}
              className="w-full bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-white font-medium py-2.5 rounded-lg text-sm transition"
            >
              Баталгаажуулах ба Хадгалах
            </button>
          </div>
        ) : (
          <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
            <div className="text-4xl mb-3">✅</div>
            <h3 className="font-semibold text-green-800 mb-1">Шийдвэр бүртгэгдлээ</h3>
            <p className="text-green-700 text-sm mb-4">Таны шийдвэр болон AI-ийн хариулт audit log-д хадгалагдлаа</p>
            <Link href="/dashboard" className="text-blue-600 text-sm hover:underline">← Хяналтын самбар руу буцах</Link>
          </div>
        )}
      </div>
    </AppShell>
  )
}

function ClinicalInputReview({ caseData }: { caseData: ClinicalCase }) {
  const attachments = caseData.attachments ?? []
  const labAttachments = attachments.filter((attachment) => attachment.section === 'labs')
  const labAbnormal = caseData.labResults.filter((lab) => lab.abnormalFlag).length

  return (
    <section className="bg-white rounded-xl border border-blue-100 shadow-sm p-6 mb-6">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="font-semibold text-slate-900">AI-д ашигласан оруулсан мэдээлэл</h2>
          <p className="text-sm text-slate-500 mt-1">{caseData.chiefComplaint}</p>
        </div>
        <Link href={`/cases/${caseData.id}`} className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          Оруулсан мэдээлэл засах
        </Link>
      </div>

      <div className="grid grid-cols-5 gap-3 mb-4">
        <InputMetric label="Симптом" value={caseData.symptoms.length} />
        <InputMetric
          label="Лаб"
          value={caseData.labResults.length + labAttachments.length}
          detail={labAbnormal ? `${labAbnormal} хэвийн бус` : labAttachments.length ? `${labAttachments.length} зураг` : undefined}
        />
        <InputMetric label="Эм" value={caseData.medications.length} />
        <InputMetric label="Зураг" value={attachments.length} />
        <InputMetric label="Улаан дохио" value={caseData.hasRedFlag ? 1 : 0} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <InputList
          title="Симптом"
          empty="Симптом оруулаагүй"
          items={caseData.symptoms.slice(0, 3).map((symptom) => `${symptom.name} · ${symptom.duration || 'хугацаа байхгүй'}`)}
        />
        <InputList
          title="Лаборатори"
          empty="Лаборатори оруулаагүй"
          items={[
            ...caseData.labResults.slice(0, 3).map((lab) => `${lab.testName}: ${lab.value} ${lab.unit}${lab.abnormalFlag ? ' · хэвийн бус' : ''}`),
            ...labAttachments.slice(0, 3).map((attachment) => `Лаб зураг: ${attachment.fileName}`),
          ]}
        />
        <InputList
          title="Эм & зураг"
          empty="Эм, зураг оруулаагүй"
          items={[
            ...caseData.medications.slice(0, 2).map((medication) => `${medication.name} ${medication.dose}`.trim()),
            ...attachments.slice(0, 2).map((attachment) => `${attachment.fileName} · ${attachment.section}`),
          ]}
        />
      </div>
    </section>
  )
}

function InputMetric({ label, value, detail }: { label: string; value: number; detail?: string }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {detail && <p className="text-xs text-red-600">{detail}</p>}
    </div>
  )
}

function InputList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{title}</h3>
      {items.length > 0 ? (
        <ul className="space-y-1.5">
          {items.map((item, index) => (
            <li key={`${title}-${index}-${item}`} className="text-sm text-slate-700 rounded-md bg-slate-50 px-3 py-2">{item}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-400 rounded-md bg-slate-50 px-3 py-2">{empty}</p>
      )}
    </div>
  )
}
