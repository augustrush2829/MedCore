import 'server-only'
import { geminiJSON, geminiConfigured, parseDataUrl } from './gemini'
import {
  buildFallbackContent,
  type ExplanationContent,
  type ExplanationInput,
  type ExtractionResult,
  type LabObservation,
} from '../patient-store'

const SYSTEM = `Чи бол MedCore эмнэлзүйн системийн өвчтөнд зориулсан тайлбарлагч.
Эмчийн оношийг ОРЛОХГҮЙ. Зөвхөн өвчтөнд ойлгомжтой, энгийн монгол хэлээр тайлбарла.
Айдас төрүүлэхгүй, гэхдээ үнэн зөв байх. Онош ТОГТООХГҮЙ — зөвхөн ерөнхий мэдээлэл өг.
Хариуг ЗААВАЛ доорх JSON бүтэцтэй, монгол хэлээр буцаа.`

interface GeminiContent {
  summary: string
  lab_meaning: string
  plain_language: string[]
  next_questions: string[]
  safety_notes: string[]
}

export async function generateExplanationContent(input: ExplanationInput): Promise<{
  content: ExplanationContent
  source: 'gemini' | 'fallback'
}> {
  const fallback = buildFallbackContent(input)
  if (!geminiConfigured()) return { content: fallback, source: 'fallback' }

  const prompt = `Өвчтөний оруулсан мэдээлэл:
- Эмчийн дүгнэлт/онош: ${input.diagnosis_text ?? 'байхгүй'}
- Шинжилгээ: ${input.lab_name ?? 'байхгүй'}
- Үр дүн: ${input.lab_value ?? '?'} ${input.lab_unit ?? ''}
- Хэвийн хэмжээ: ${input.reference_range ?? 'байхгүй'}
- Өвчтөний асуулт: ${input.patient_question ?? 'байхгүй'}

Дараах JSON форматаар хариул (бүх текст монгол хэлээр):
{
  "summary": "1-2 өгүүлбэр хураангуй",
  "lab_meaning": "шинжилгээний үр дүн юу гэсэн үг болохыг 1-2 өгүүлбэрээр",
  "plain_language": ["ойлгомжтой тайлбар 1", "тайлбар 2"],
  "next_questions": ["эмчээс асуух асуулт 1", "асуулт 2", "асуулт 3"],
  "safety_notes": ["анхаарах шинж тэмдэг 1"]
}`

  try {
    const g = await geminiJSON<GeminiContent>(prompt, { systemInstruction: SYSTEM, temperature: 0.3 })
    return {
      content: {
        summary: g.summary || fallback.summary,
        lab_meaning: g.lab_meaning || fallback.lab_meaning,
        plain_language: Array.isArray(g.plain_language) && g.plain_language.length ? g.plain_language : fallback.plain_language,
        next_questions: Array.isArray(g.next_questions) && g.next_questions.length ? g.next_questions : fallback.next_questions,
        safety_notes: Array.isArray(g.safety_notes) && g.safety_notes.length ? g.safety_notes : fallback.safety_notes,
        disclaimer: fallback.disclaimer,  // disclaimer тогтмол байх
      },
      source: 'gemini',
    }
  } catch (err) {
    console.warn('[gemini] explanation generation failed, using fallback:', (err as Error).message)
    return { content: fallback, source: 'fallback' }
  }
}

// ---------------------------------------------------------------------------
// Gemini Vision: шинжилгээний зургийг уншиж lab утга гаргаж аваад тайлбарлах
// ---------------------------------------------------------------------------
interface VisionResult {
  report_type: string
  ocr_text: string
  observations: {
    test_name: string
    value: string | null
    unit: string | null
    reference_range: string | null
    abnormal_flag: boolean | null
  }[]
  content: GeminiContent
}

const VISION_SYSTEM = `Чи бол MedCore-ийн эмнэлгийн шинжилгээний баримт уншигч AI.
Эмчийн оношийг ОРЛОХГҮЙ. Баримтаас бодит мэдээллийг л унш — таамаглахгүй.
Олон төрлийн баримт ирж болно: тоон лабораторийн хариу, CT/MRI/рентген зэрэг
ДҮРС ОНОШИЛГООНЫ хариу, эмгэг судлалын хариу гэх мэт.
- Тоон лаб хариунд: observations-д утга, нэгж, хэвийн хязгаарыг гаргана.
- Дүрс оношилгоонд (CT/MRI/X-ray): тоон утга байхгүй байж болно. Тэр үед
  observations-ийг хоосон орхиод, гол findings болон дүгнэлтийг content дотор
  энгийнээр тайлбарла.
Хэрэв баримт бүдэг, уншигдахгүй бол observations хоосон, content-д "уншигдахгүй" гэж бич.
Хариуг ЗААВАЛ JSON, бүх тайлбарыг энгийн монгол хэлээр буцаа.`

export async function extractFromImage(
  input: ExplanationInput,
  imageDataUrl: string,
): Promise<{ content: ExplanationContent; extracted: ExtractionResult; source: 'gemini-vision' | 'fallback' }> {
  const fallbackContent = buildFallbackContent(input)
  const img = parseDataUrl(imageDataUrl)

  if (!geminiConfigured() || !img) {
    return {
      content: fallbackContent,
      extracted: {
        status: img ? 'requires_review' : 'failed',
        model: 'none',
        observations: [],
        notes: ['Зургийг автоматаар уншиж чадсангүй. Эмчийн хяналт шаардлагатай.'],
        ocr_text: null,
      },
      source: 'fallback',
    }
  }

  const prompt = `Энэ бол өвчтөний эмнэлгийн шинжилгээний баримт (зураг).
${input.patient_question ? `Өвчтөний асуулт: ${input.patient_question}` : ''}

1. Баримт доторх БҮХ текстийг уншиж "ocr_text"-д бичнэ.
2. "report_type"-д баримтын төрлийг бич: "lab" (тоон лаб), "imaging" (CT/MRI/рентген), "other".
3. Хэрэв ТООН лаб утга байвал observations-д гаргана. Дүрс оношилгоо бол observations хоосон байж болно.
4. content дотор өвчтөнд ойлгомжтой энгийн монгол тайлбар бич:
   - summary: гол дүгнэлт юу болохыг 1-2 өгүүлбэрээр
   - lab_meaning: гол findings/үзүүлэлт юу гэсэн үг (дүрс оношилгоо бол олдсон өөрчлөлтийг тайлбарла)
   - plain_language: энгийн үгээр 2-3 тайлбар
   - next_questions: эмчээс асуух 3 асуулт
   - safety_notes: анхаарах шинж тэмдэг

Дараах JSON форматаар хариул (string дотор шинэ мөр бүү ашигла):
{
  "report_type": "lab|imaging|other",
  "ocr_text": "баримтаас уншсан бүх текст",
  "observations": [
    {"test_name": "ALT", "value": "120", "unit": "U/L", "reference_range": "7-40", "abnormal_flag": true}
  ],
  "content": {
    "summary": "...",
    "lab_meaning": "...",
    "plain_language": ["...", "..."],
    "next_questions": ["...", "...", "..."],
    "safety_notes": ["..."]
  }
}`

  try {
    const v = await geminiJSON<VisionResult>(prompt, {
      systemInstruction: VISION_SYSTEM,
      temperature: 0.2,
      image: img,
      timeoutMs: 60_000,
    })

    const observations: LabObservation[] = Array.isArray(v.observations)
      ? v.observations.map((o) => ({
        test_name: o.test_name ?? '',
        value: o.value ?? null,
        unit: o.unit ?? null,
        reference_range: o.reference_range ?? null,
        abnormal_flag: o.abnormal_flag ?? null,
        source: 'gemini-vision-pro',
        confidence: 80,
      }))
      : []

    const c = v.content ?? ({} as GeminiContent)
    return {
      content: {
        summary: c.summary || fallbackContent.summary,
        lab_meaning: c.lab_meaning || fallbackContent.lab_meaning,
        plain_language: Array.isArray(c.plain_language) && c.plain_language.length ? c.plain_language : fallbackContent.plain_language,
        next_questions: Array.isArray(c.next_questions) && c.next_questions.length ? c.next_questions : fallbackContent.next_questions,
        safety_notes: Array.isArray(c.safety_notes) && c.safety_notes.length ? c.safety_notes : fallbackContent.safety_notes,
        disclaimer: fallbackContent.disclaimer,
      },
      extracted: {
        // imaging/other баримтад тоон observations байхгүй ч 'processed' — тайлбар гарсан
        status: 'processed',
        model: process.env.GEMINI_MODEL || 'gemini-2.5-flash-lite',
        observations,
        notes: observations.length
          ? ['Зургийг Gemini Vision уншиж structured дата гаргав.']
          : [
            `Баримтын төрөл: ${v.report_type || 'тодорхойгүй'}. Тоон лаб утга биш тул`,
            'findings-ийг доорх тайлбараас уншина уу. Эцсийн дүгнэлтийг эмч гаргана.',
          ],
        ocr_text: v.ocr_text ?? null,
      },
      source: 'gemini-vision',
    }
  } catch (err) {
    console.warn('[gemini-vision] extraction failed, using fallback:', (err as Error).message)
    return {
      content: fallbackContent,
      extracted: {
        status: 'failed',
        model: process.env.GEMINI_MODEL || 'gemini-2.5-flash-lite',
        observations: [],
        notes: ['Зургийг боловсруулахад алдаа гарлаа. Эмчийн хяналт шаардлагатай.'],
        ocr_text: null,
      },
      source: 'fallback',
    }
  }
}
