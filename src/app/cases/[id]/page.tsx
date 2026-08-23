'use client'

import { use, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import AppShell from '@/components/layout/AppShell'
import Link from 'next/link'
import { clinicalApi } from '@/lib/clinical-api'
import type { CaseAttachment, CaseAttachmentSection, ClinicalCase, LabResult, Medication, Symptom } from '@/types'

const SECTIONS = ['Үндсэн мэдээлэл', 'Симптом', 'Амин үзүүлэлт', 'Лаборатори', 'Эм & Найрлага', 'Харшил']
const INPUT_CLASS = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'

type VitalSign = {
  id: string
  name: string
  value: string
  unit: string
}

type Allergy = {
  id: string
  substance: string
  reaction: string
  severity: 'mild' | 'moderate' | 'severe'
}

type EditableCase = ClinicalCase & {
  clinicalNote: string
  onsetDate: string
  comorbidities: string
  vitalSigns: VitalSign[]
  allergies: Allergy[]
}

const DEFAULT_VITALS: VitalSign[] = [
  { id: 'v1', name: 'Цусны даралт', value: '', unit: 'mmHg' },
  { id: 'v2', name: 'Пульс', value: '', unit: 'bpm' },
  { id: 'v3', name: 'Халуун', value: '', unit: '°C' },
  { id: 'v4', name: 'SpO2', value: '', unit: '%' },
  { id: 'v5', name: 'Амьсгалын тоо', value: '', unit: '/мин' },
  { id: 'v6', name: 'Жин', value: '', unit: 'кг' },
]

function createEditableCase(caseData: ClinicalCase): EditableCase {
  const saved = caseData as Partial<EditableCase>
  return {
    ...caseData,
    attachments: caseData.attachments ?? [],
    clinicalNote: saved.clinicalNote ?? '',
    onsetDate: saved.onsetDate ?? '',
    comorbidities: saved.comorbidities ?? '',
    vitalSigns: saved.vitalSigns ?? DEFAULT_VITALS.map((vital) => ({ ...vital })),
    allergies: saved.allergies ?? [],
  }
}

function nextId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [caseData, setCaseData] = useState<EditableCase | null>(null)
  const [activeSection, setActiveSection] = useState(0)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    clinicalApi.case(id)
      .then((result) => setCaseData(createEditableCase(result)))
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Case API алдаа гарлаа'))
  }, [id])

  const updateCase = (patch: Partial<EditableCase>) => {
    setNotice('')
    setCaseData((current) => current ? { ...current, ...patch, updatedAt: new Date().toISOString() } : current)
  }

  const handleSave = async () => {
    if (!caseData) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const saved = await clinicalApi.updateCase(caseData.id, caseData)
      setCaseData(createEditableCase(saved))
      setNotice('Хадгаллаа')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Case API хадгалах алдаа гарлаа')
    } finally {
      setSaving(false)
    }
  }

  const handleAnalyze = async () => {
    if (!caseData) return
    setAnalyzing(true)
    setError('')
    try {
      await clinicalApi.updateCase(caseData.id, caseData)
      await clinicalApi.analyzeCase(caseData.id)
      window.location.href = `/cases/${caseData.id}/ai-result`
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Case API алдаа гарлаа')
      setAnalyzing(false)
    }
  }

  const handleDelete = async () => {
    if (!caseData) return
    const confirmed = window.confirm('Энэ тохиолдлыг бүр мөсөн устгах уу?')
    if (!confirmed) return
    setDeleting(true)
    setError('')
    try {
      await clinicalApi.deleteCase(caseData.id)
      window.location.href = '/cases'
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Case API устгах алдаа гарлаа')
      setDeleting(false)
    }
  }

  if (error) return <AppShell><div className="p-8 text-sm text-red-600">{error}</div></AppShell>
  if (!caseData) return <AppShell><div className="p-8 text-sm text-slate-500">Case API-аас уншиж байна...</div></AppShell>

  return (
    <AppShell>
      <div className="p-8 max-w-5xl">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-6">
          <Link href="/dashboard" className="hover:text-slate-600">Хяналтын самбар</Link>
          <span>/</span>
          <span className="text-slate-700">{caseData.chiefComplaint}</span>
        </div>

        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">{caseData.patientName}</h1>
            <p className="text-slate-500 text-sm mt-0.5">{caseData.chiefComplaint}</p>
            <p className="text-slate-400 text-xs mt-1">Сүүлд хадгалсан: {new Date(caseData.updatedAt).toLocaleString('mn-MN')}</p>
            {notice && <p className="text-green-600 text-xs mt-1">{notice}</p>}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleDelete}
              disabled={deleting || saving || analyzing}
              className="border border-red-200 bg-white hover:bg-red-50 disabled:opacity-50 text-red-600 px-4 py-2.5 rounded-lg text-sm font-medium transition"
            >
              {deleting ? 'Устгаж байна...' : 'Тохиолдол устгах'}
            </button>
            <button
              onClick={handleSave}
              disabled={saving || analyzing || deleting}
              className="border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50 text-slate-700 px-4 py-2.5 rounded-lg text-sm font-medium transition"
            >
              {saving ? 'Хадгалж байна...' : 'Хадгалах'}
            </button>
            <button
              onClick={handleAnalyze}
              disabled={analyzing || saving || deleting}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition flex items-center gap-2"
            >
              {analyzing ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  AI шинжилж байна...
                </>
              ) : '🧠 AI шинжилгээ хийх'}
            </button>
          </div>
        </div>

        <div className="flex gap-6">
          <div className="w-44 shrink-0">
            <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
              {SECTIONS.map((section, index) => (
                <button
                  key={section}
                  onClick={() => setActiveSection(index)}
                  className={`w-full text-left px-4 py-3 text-sm border-b border-slate-50 last:border-0 transition ${
                    activeSection === index
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {section}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1">
            <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6">
              {activeSection === 0 && <BasicInfoSection data={caseData} onChange={updateCase} />}
              {activeSection === 1 && <SymptomsSection data={caseData} onChange={updateCase} />}
              {activeSection === 2 && <VitalsSection data={caseData} onChange={updateCase} />}
              {activeSection === 3 && <LabSection data={caseData} onChange={updateCase} />}
              {activeSection === 4 && <MedSection data={caseData} onChange={updateCase} />}
              {activeSection === 5 && <AllergySection data={caseData} onChange={updateCase} />}
            </div>

            <div className="flex justify-between mt-4">
              <button
                onClick={() => setActiveSection(Math.max(0, activeSection - 1))}
                disabled={activeSection === 0}
                className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-40 transition"
              >
                ← Өмнөх
              </button>
              {activeSection < SECTIONS.length - 1 ? (
                <button
                  onClick={() => setActiveSection(activeSection + 1)}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                  Дараах →
                </button>
              ) : (
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60 transition"
                >
                  🧠 AI шинжилгээ хийх
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}

function BasicInfoSection({ data, onChange }: { data: EditableCase; onChange: (patch: Partial<EditableCase>) => void }) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-slate-900">Үндсэн мэдээлэл</h3>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Гол зовиур" className="col-span-1">
          <textarea
            value={data.chiefComplaint}
            onChange={(event) => onChange({ chiefComplaint: event.target.value })}
            rows={3}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
          />
        </Field>
        <Field label="Эмчилгээний тэмдэглэл">
          <textarea
            value={data.clinicalNote}
            onChange={(event) => onChange({ clinicalNote: event.target.value })}
            placeholder="Нэмэлт тэмдэглэл..."
            rows={3}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
          />
        </Field>
        <Field label="Өвчний эхэлсэн огноо">
          <input
            type="date"
            value={data.onsetDate}
            onChange={(event) => onChange({ onsetDate: event.target.value })}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
        </Field>
        <Field label="Хавсарсан өвчин">
          <input
            type="text"
            value={data.comorbidities}
            onChange={(event) => onChange({ comorbidities: event.target.value })}
            placeholder="ЧЭӨ, чихрийн шижин..."
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
        </Field>
      </div>
      <ImageAttachmentPanel data={data} onChange={onChange} section="basic" title="Үндсэн мэдээлэлтэй холбоотой зураг" />
    </div>
  )
}

function SymptomsSection({ data, onChange }: { data: EditableCase; onChange: (patch: Partial<EditableCase>) => void }) {
  const [draft, setDraft] = useState<Omit<Symptom, 'id'>>({
    name: '',
    severity: 'mild',
    onsetDate: '',
    duration: '',
    note: '',
  })

  const addSymptom = () => {
    if (!draft.name.trim()) return
    onChange({ symptoms: [...data.symptoms, { ...draft, id: nextId('symptom') }] })
    setDraft({ name: '', severity: 'mild', onsetDate: '', duration: '', note: '' })
  }

  const removeSymptom = (id: string) => {
    onChange({ symptoms: data.symptoms.filter((symptom) => symptom.id !== id) })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-900">Симптомууд</h3>
        <button onClick={addSymptom} className="text-blue-600 text-sm hover:underline">+ Нэмэх</button>
      </div>
      <div className="grid grid-cols-4 gap-3 mb-4">
        <input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="Симптом" className={INPUT_CLASS} />
        <select value={draft.severity} onChange={(event) => setDraft({ ...draft, severity: event.target.value as Symptom['severity'] })} className={INPUT_CLASS}>
          <option value="mild">Хөнгөн</option>
          <option value="moderate">Дунд</option>
          <option value="severe">Хүнд</option>
        </select>
        <input type="date" value={draft.onsetDate} onChange={(event) => setDraft({ ...draft, onsetDate: event.target.value })} className={INPUT_CLASS} />
        <input value={draft.duration} onChange={(event) => setDraft({ ...draft, duration: event.target.value })} placeholder="Үргэлжилсэн хугацаа" className={INPUT_CLASS} />
        <input value={draft.note ?? ''} onChange={(event) => setDraft({ ...draft, note: event.target.value })} placeholder="Тэмдэглэл" className={`${INPUT_CLASS} col-span-4`} />
      </div>
      <div className="space-y-3">
        {data.symptoms.map((symptom) => (
          <ClinicalRow key={symptom.id} onRemove={() => removeSymptom(symptom.id)}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-slate-900 text-sm">{symptom.name}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${severityClass(symptom.severity)}`}>
                {severityLabel(symptom.severity)}
              </span>
            </div>
            <div className="flex gap-4 text-xs text-slate-500">
              <span>📅 {symptom.onsetDate || 'Огноо байхгүй'}</span>
              <span>⏱ {symptom.duration || 'Хугацаа байхгүй'}</span>
              {symptom.note && <span>📝 {symptom.note}</span>}
            </div>
          </ClinicalRow>
        ))}
        {data.symptoms.length === 0 && <EmptyState label="Симптом нэмэгдээгүй байна" />}
      </div>
      <ImageAttachmentPanel data={data} onChange={onChange} section="symptoms" title="Симптомтой холбоотой зураг" />
    </div>
  )
}

function VitalsSection({ data, onChange }: { data: EditableCase; onChange: (patch: Partial<EditableCase>) => void }) {
  const updateVital = (id: string, value: string) => {
    onChange({ vitalSigns: data.vitalSigns.map((vital) => vital.id === id ? { ...vital, value } : vital) })
  }

  return (
    <div>
      <h3 className="font-semibold text-slate-900 mb-4">Амин үзүүлэлт</h3>
      <div className="grid grid-cols-3 gap-4">
        {data.vitalSigns.map((vital) => (
          <Field key={vital.id} label={vital.name}>
            <div className="flex">
              <input
                type="text"
                value={vital.value}
                onChange={(event) => updateVital(vital.id, event.target.value)}
                placeholder={vital.name === 'Цусны даралт' ? '120/80' : ''}
                className="flex-1 border border-slate-200 rounded-l-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
              <span className="border border-l-0 border-slate-200 rounded-r-lg px-2.5 py-2 text-xs text-slate-400 bg-slate-50">{vital.unit}</span>
            </div>
          </Field>
        ))}
      </div>
      <ImageAttachmentPanel data={data} onChange={onChange} section="vitals" title="Амин үзүүлэлтийн зураг" />
    </div>
  )
}

function LabSection({ data, onChange }: { data: EditableCase; onChange: (patch: Partial<EditableCase>) => void }) {
  const [extracting, setExtracting] = useState(false)
  const [extractMessage, setExtractMessage] = useState('')
  const [draft, setDraft] = useState<Omit<LabResult, 'id' | 'abnormalFlag'>>({
    testName: '',
    value: 0,
    unit: '',
    referenceRangeLow: 0,
    referenceRangeHigh: 0,
    collectedAt: new Date().toISOString().slice(0, 10),
  })

  const addLab = () => {
    if (!draft.testName.trim() || !draft.unit.trim()) return
    const abnormalFlag = draft.value < draft.referenceRangeLow || draft.value > draft.referenceRangeHigh
    onChange({ labResults: [...data.labResults, { ...draft, id: nextId('lab'), abnormalFlag }] })
    setDraft({ testName: '', value: 0, unit: '', referenceRangeLow: 0, referenceRangeHigh: 0, collectedAt: new Date().toISOString().slice(0, 10) })
  }

  const removeLab = (id: string) => {
    onChange({ labResults: data.labResults.filter((lab) => lab.id !== id) })
  }

  const extractFromImages = async () => {
    setExtracting(true)
    setExtractMessage('')
    try {
      await clinicalApi.updateCase(data.id, data)
      const result = await clinicalApi.extractLabs(data.id)
      onChange({
        labResults: result.case.labResults,
        attachments: result.case.attachments ?? data.attachments,
      })
      setExtractMessage(result.added > 0 ? `${result.added} lab мөр зурагнаас нэмлээ. Patient labs-д ${result.patientLabsAdded} мөр хадгаллаа.` : 'Шинэ lab мөр нэмэгдсэнгүй.')
    } catch (caught) {
      setExtractMessage(caught instanceof Error ? caught.message : 'Зурагнаас lab уншихад алдаа гарлаа')
    } finally {
      setExtracting(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-900">Лабораторийн хариу</h3>
        <div className="flex items-center gap-3">
          <button onClick={extractFromImages} disabled={extracting} className="text-blue-600 disabled:text-slate-400 text-sm hover:underline">
            {extracting ? 'Зураг уншиж байна...' : 'Зурагнаас lab унших'}
          </button>
          <button onClick={addLab} className="text-blue-600 text-sm hover:underline">+ Нэмэх</button>
        </div>
      </div>
      {extractMessage && (
        <div className={`mb-3 rounded-lg border px-3 py-2 text-sm ${extractMessage.includes('алдаа') || extractMessage.includes('тохируулагдаагүй') ? 'border-red-200 bg-red-50 text-red-700' : 'border-blue-200 bg-blue-50 text-blue-700'}`}>
          {extractMessage}
        </div>
      )}
      <div className="grid grid-cols-6 gap-3 mb-4">
        <input value={draft.testName} onChange={(event) => setDraft({ ...draft, testName: event.target.value })} placeholder="ALT" className={INPUT_CLASS} />
        <input type="number" value={draft.value} onChange={(event) => setDraft({ ...draft, value: Number(event.target.value) })} placeholder="Утга" className={INPUT_CLASS} />
        <input value={draft.unit} onChange={(event) => setDraft({ ...draft, unit: event.target.value })} placeholder="U/L" className={INPUT_CLASS} />
        <input type="number" value={draft.referenceRangeLow} onChange={(event) => setDraft({ ...draft, referenceRangeLow: Number(event.target.value) })} placeholder="Доод" className={INPUT_CLASS} />
        <input type="number" value={draft.referenceRangeHigh} onChange={(event) => setDraft({ ...draft, referenceRangeHigh: Number(event.target.value) })} placeholder="Дээд" className={INPUT_CLASS} />
        <input type="date" value={draft.collectedAt} onChange={(event) => setDraft({ ...draft, collectedAt: event.target.value })} className={INPUT_CLASS} />
      </div>
      {data.labResults.length > 0 ? (
        <div className="overflow-hidden rounded-lg border border-slate-100">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-slate-500">Шинжилгээ</th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-slate-500">Үр дүн</th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-slate-500">Хэвийн хязгаар</th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-slate-500">Огноо</th>
                <th className="px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.labResults.map((lab) => (
                <tr key={lab.id} className={lab.abnormalFlag ? 'bg-red-50' : ''}>
                  <td className="px-4 py-3 font-medium text-slate-900">{lab.testName}</td>
                  <td className="px-4 py-3">
                    <span className={`font-semibold ${lab.abnormalFlag ? 'text-red-600' : 'text-green-600'}`}>{lab.value} {lab.unit}</span>
                    {lab.abnormalFlag && <span className="ml-1 text-xs text-red-500">⚠</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{lab.referenceRangeLow}–{lab.referenceRangeHigh} {lab.unit}</td>
                  <td className="px-4 py-3 text-slate-400">
                    {lab.collectedAt || 'Эмчээс огноо тодруулах'}
                    {lab.dateReviewRequired && <span className="ml-1 text-xs text-amber-600">шаардлагатай</span>}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => removeLab(lab.id)} className="text-xs text-red-500 hover:underline">Устгах</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState label="Лабораторийн хариу нэмэгдээгүй" />}
      <ImageAttachmentPanel data={data} onChange={onChange} section="labs" title="Лабораторийн хариуны зураг" />
    </div>
  )
}

function MedSection({ data, onChange }: { data: EditableCase; onChange: (patch: Partial<EditableCase>) => void }) {
  const [draft, setDraft] = useState({
    name: '',
    dose: '',
    route: 'амаар',
    frequency: '',
    startDate: new Date().toISOString().slice(0, 10),
    ingredients: '',
    status: 'active' as Medication['status'],
  })

  const addMedication = () => {
    if (!draft.name.trim()) return
    onChange({
      medications: [
        ...data.medications,
        {
          id: nextId('med'),
          name: draft.name,
          dose: draft.dose,
          route: draft.route,
          frequency: draft.frequency,
          startDate: draft.startDate,
          ingredients: draft.ingredients.split(',').map((item) => item.trim()).filter(Boolean),
          status: draft.status,
        },
      ],
    })
    setDraft({ name: '', dose: '', route: 'амаар', frequency: '', startDate: new Date().toISOString().slice(0, 10), ingredients: '', status: 'active' })
  }

  const removeMedication = (id: string) => {
    onChange({ medications: data.medications.filter((medication) => medication.id !== id) })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-900">Эм & Найрлага</h3>
        <button onClick={addMedication} className="text-blue-600 text-sm hover:underline">+ Нэмэх</button>
      </div>
      <div className="grid grid-cols-6 gap-3 mb-4">
        <input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="Эмийн нэр" className={INPUT_CLASS} />
        <input value={draft.dose} onChange={(event) => setDraft({ ...draft, dose: event.target.value })} placeholder="Тун" className={INPUT_CLASS} />
        <input value={draft.route} onChange={(event) => setDraft({ ...draft, route: event.target.value })} placeholder="Зам" className={INPUT_CLASS} />
        <input value={draft.frequency} onChange={(event) => setDraft({ ...draft, frequency: event.target.value })} placeholder="Давтамж" className={INPUT_CLASS} />
        <input type="date" value={draft.startDate} onChange={(event) => setDraft({ ...draft, startDate: event.target.value })} className={INPUT_CLASS} />
        <select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value as Medication['status'] })} className={INPUT_CLASS}>
          <option value="active">Идэвхтэй</option>
          <option value="stopped">Зогссон</option>
        </select>
        <input value={draft.ingredients} onChange={(event) => setDraft({ ...draft, ingredients: event.target.value })} placeholder="Найрлага, таслалаар" className={`${INPUT_CLASS} col-span-6`} />
      </div>
      <div className="space-y-3">
        {data.medications.map((medication) => (
          <ClinicalRow key={medication.id} onRemove={() => removeMedication(medication.id)}>
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-900 text-sm">{medication.name}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${medication.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                {medication.status === 'active' ? 'Идэвхтэй' : 'Зогссон'}
              </span>
            </div>
            <div className="flex flex-wrap gap-3 mt-2 text-xs text-slate-500">
              <span>💊 {medication.dose || 'Тун байхгүй'}</span>
              <span>🔄 {medication.frequency || 'Давтамж байхгүй'}</span>
              <span>📅 {medication.startDate || 'Огноо байхгүй'}-с</span>
            </div>
            {medication.ingredients.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {medication.ingredients.map((ingredient) => (
                  <span key={ingredient} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">{ingredient}</span>
                ))}
              </div>
            )}
          </ClinicalRow>
        ))}
        {data.medications.length === 0 && <EmptyState label="Эм нэмэгдээгүй байна" />}
      </div>
      <ImageAttachmentPanel data={data} onChange={onChange} section="medications" title="Эм, найрлагатай холбоотой зураг" />
    </div>
  )
}

function AllergySection({ data, onChange }: { data: EditableCase; onChange: (patch: Partial<EditableCase>) => void }) {
  const [draft, setDraft] = useState<Omit<Allergy, 'id'>>({ substance: '', reaction: '', severity: 'mild' })

  const addAllergy = () => {
    if (!draft.substance.trim()) return
    onChange({ allergies: [...data.allergies, { ...draft, id: nextId('allergy') }] })
    setDraft({ substance: '', reaction: '', severity: 'mild' })
  }

  const removeAllergy = (id: string) => {
    onChange({ allergies: data.allergies.filter((allergy) => allergy.id !== id) })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-900">Харшил</h3>
        <button onClick={addAllergy} className="text-blue-600 text-sm hover:underline">+ Нэмэх</button>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <input value={draft.substance} onChange={(event) => setDraft({ ...draft, substance: event.target.value })} placeholder="Бодис / эм" className={INPUT_CLASS} />
        <input value={draft.reaction} onChange={(event) => setDraft({ ...draft, reaction: event.target.value })} placeholder="Урвал" className={INPUT_CLASS} />
        <select value={draft.severity} onChange={(event) => setDraft({ ...draft, severity: event.target.value as Allergy['severity'] })} className={INPUT_CLASS}>
          <option value="mild">Хөнгөн</option>
          <option value="moderate">Дунд</option>
          <option value="severe">Хүнд</option>
        </select>
      </div>
      <div className="space-y-3">
        {data.allergies.map((allergy) => (
          <ClinicalRow key={allergy.id} onRemove={() => removeAllergy(allergy.id)}>
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-900 text-sm">{allergy.substance}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${severityClass(allergy.severity)}`}>{severityLabel(allergy.severity)}</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">{allergy.reaction || 'Урвалын тэмдэглэл байхгүй'}</p>
          </ClinicalRow>
        ))}
        {data.allergies.length === 0 && <EmptyState label="Бүртгэгдсэн харшил байхгүй" />}
      </div>
      <ImageAttachmentPanel data={data} onChange={onChange} section="allergies" title="Харшилтай холбоотой зураг" />
    </div>
  )
}

function ImageAttachmentPanel({
  data,
  onChange,
  section,
  title,
}: {
  data: EditableCase
  onChange: (patch: Partial<EditableCase>) => void
  section: CaseAttachmentSection
  title: string
}) {
  const attachments = (data.attachments ?? []).filter((attachment) => attachment.section === section)

  const addFiles = async (files: FileList | null) => {
    if (!files?.length) return
    const images = Array.from(files).filter((file) => file.type.startsWith('image/'))
    if (images.length === 0) return
    const uploaded = await Promise.all(images.map(readImageAttachment(section)))
    onChange({ attachments: [...(data.attachments ?? []), ...uploaded] })
  }

  const removeAttachment = (id: string) => {
    onChange({ attachments: (data.attachments ?? []).filter((attachment) => attachment.id !== id) })
  }

  return (
    <section className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
          <p className="text-xs text-slate-500">AI-д дараа ашиглах зураг, screenshot, lab/photo evidence энд хадгалагдана.</p>
        </div>
        <label className="cursor-pointer rounded-lg bg-white border border-slate-200 px-3 py-2 text-xs font-medium text-blue-600 hover:bg-blue-50">
          Зураг нэмэх
          <input type="file" accept="image/*" multiple className="hidden" onChange={(event) => addFiles(event.target.files)} />
        </label>
      </div>
      {attachments.length > 0 ? (
        <div className="grid grid-cols-3 gap-3">
          {attachments.map((attachment) => (
            <div key={attachment.id} className="overflow-hidden rounded-lg border border-slate-200 bg-white">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={attachment.dataUrl} alt={attachment.fileName} className="h-28 w-full object-cover bg-slate-100" />
              <div className="p-2">
                <p className="truncate text-xs font-medium text-slate-700">{attachment.fileName}</p>
                <p className="text-[11px] text-slate-400">{Math.round(attachment.sizeBytes / 1024)} KB · {new Date(attachment.createdAt).toLocaleString('mn-MN')}</p>
                <button onClick={() => removeAttachment(attachment.id)} className="mt-1 text-xs text-red-500 hover:underline">Устгах</button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border-2 border-dashed border-slate-200 bg-white py-6 text-center text-sm text-slate-400">
          Зураг нэмэгдээгүй байна
        </div>
      )}
    </section>
  )
}

function readImageAttachment(section: CaseAttachmentSection) {
  return (file: File) => new Promise<CaseAttachment>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      resolve({
        id: nextId('attachment'),
        section,
        fileName: file.name,
        contentType: file.type,
        sizeBytes: file.size,
        dataUrl: String(reader.result),
        createdAt: new Date().toISOString(),
      })
    }
    reader.onerror = () => reject(new Error('Зураг уншихад алдаа гарлаа'))
    reader.readAsDataURL(file)
  })
}

function Field({ label, className = '', children }: { label: string; className?: string; children: ReactNode }) {
  return (
    <div className={className}>
      <label className="block text-xs font-medium text-slate-500 mb-1.5">{label}</label>
      {children}
    </div>
  )
}

function ClinicalRow({ children, onRemove }: { children: ReactNode; onRemove: () => void }) {
  return (
    <div className="border border-slate-100 rounded-lg p-4 bg-slate-50">
      {children}
      <button onClick={onRemove} className="text-xs text-red-500 hover:underline mt-3">Устгах</button>
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="text-center py-8 text-slate-400 text-sm border-2 border-dashed border-slate-200 rounded-lg">
      {label}
    </div>
  )
}

function severityLabel(severity: 'mild' | 'moderate' | 'severe') {
  return severity === 'severe' ? 'Хүнд' : severity === 'moderate' ? 'Дунд' : 'Хөнгөн'
}

function severityClass(severity: 'mild' | 'moderate' | 'severe') {
  return severity === 'severe'
    ? 'bg-red-100 text-red-600'
    : severity === 'moderate'
      ? 'bg-amber-100 text-amber-600'
      : 'bg-green-100 text-green-600'
}
