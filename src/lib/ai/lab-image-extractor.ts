import 'server-only'
import type { LabResult } from '@/types'
import { geminiConfigured, geminiJSON, parseDataUrl } from './gemini'

type ExtractedLab = {
  testName: string
  value: number | null
  unit: string
  referenceRange: string | null
  referenceRangeLow: number | null
  referenceRangeHigh: number | null
  abnormalFlag: boolean | null
  collectedAt: string | null
}

type LabImageResponse = {
  collectedAt: string | null
  labs: ExtractedLab[]
  notes: string[]
}

const SYSTEM = `Чи лабораторийн шинжилгээний зурагнаас structured lab мөр уншдаг extractor.
Зөвхөн зураг дээр байгаа бодит test/result/reference range/unit/flag мэдээллийг JSON болго.
Таамаглахгүй. Уншигдахгүй мөрийг алгас.
Flag High/Low/Slight abnormal/Abnormal бол abnormalFlag=true, Normal бол false.
Хариу зөвхөн JSON байна.`

function nextLabId() {
  return `lab-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

function parseRange(range: string | null): { low: number; high: number } {
  if (!range) return { low: 0, high: 0 }
  const bounded = range.match(/([\d.]+)\s*[-–]\s*([\d.]+)/)
  if (bounded) return { low: Number(bounded[1]), high: Number(bounded[2]) }
  const lessThan = range.match(/<\s*([\d.]+)/)
  if (lessThan) return { low: 0, high: Number(lessThan[1]) }
  const greaterThan = range.match(/>\s*([\d.]+)/)
  if (greaterThan) return { low: Number(greaterThan[1]), high: Number.POSITIVE_INFINITY }
  return { low: 0, high: 0 }
}

function normalizeDate(value: string | null) {
  if (!value) return null
  const iso = value.match(/(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/)
  if (iso) return `${iso[1]}-${iso[2].padStart(2, '0')}-${iso[3].padStart(2, '0')}`
  const us = value.match(/(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})/)
  if (us) return `${us[3]}-${us[1].padStart(2, '0')}-${us[2].padStart(2, '0')}`
  return null
}

export async function extractLabResultsFromImage(dataUrl: string): Promise<LabResult[]> {
  if (!geminiConfigured()) {
    throw new Error('GEMINI_API_KEY тохируулагдаагүй тул зурагнаас lab унших боломжгүй байна. .env.local файлд GEMINI_API_KEY=... нэмээд dev server restart хийнэ үү')
  }

  const image = parseDataUrl(dataUrl)
  if (!image) throw new Error('Зургийн data URL формат буруу байна')

  const prompt = `Энэ лабораторийн report image-ээс бүх шинжилгээний мөрийг унш.
CBC, metabolic panel, liver function, lipid profile, urinalysis г.м бүх section-ийг хамруул.

JSON schema:
{
  "collectedAt": "2026-06-02",
  "labs": [
    {
      "testName": "White Blood Cells",
      "value": 11.8,
      "unit": "x10^9/L",
      "referenceRange": "4.0 - 10.0",
      "referenceRangeLow": 4.0,
      "referenceRangeHigh": 10.0,
      "abnormalFlag": true,
      "collectedAt": "2026-06-02"
    }
  ],
  "notes": ["уншигдаагүй мөр байвал бич"]
}

Дүрэм:
- value тоон биш бол value=null.
- referenceRangeLow/High тодорхойгүй бол null.
- Normal flag=false, High/Low/Slight abnormal=true.
- Date Collected/Collected date байвал YYYY-MM-DD болгон collectedAt-д бич. Огноо байхгүй/уншигдахгүй бол collectedAt=null.
- Test name, unit-ийг зураг дээрхээр нь бич.`

  const extracted = await geminiJSON<LabImageResponse>(prompt, {
    systemInstruction: SYSTEM,
    temperature: 0.1,
    image,
    timeoutMs: 60_000,
  })

  return (extracted.labs ?? [])
    .filter((lab) => lab.testName?.trim())
    .map((lab) => {
      const parsed = parseRange(lab.referenceRange)
      const labCollectedAt = normalizeDate(lab.collectedAt) ?? normalizeDate(extracted.collectedAt)
      const low = lab.referenceRangeLow ?? parsed.low
      const high = lab.referenceRangeHigh ?? parsed.high
      const value = typeof lab.value === 'number' ? lab.value : 0
      const abnormalFlag =
        lab.abnormalFlag ??
        (typeof lab.value === 'number' && Number.isFinite(high) ? lab.value < low || lab.value > high : false)

      return {
        id: nextLabId(),
        testName: lab.testName.trim(),
        value,
        unit: lab.unit ?? '',
        referenceRangeLow: Number.isFinite(low) ? low : 0,
        referenceRangeHigh: Number.isFinite(high) ? high : 0,
        abnormalFlag,
        collectedAt: labCollectedAt ?? '',
        dateReviewRequired: !labCollectedAt,
      }
    })
}
