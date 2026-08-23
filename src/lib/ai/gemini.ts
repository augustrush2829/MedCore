import 'server-only'

const API_BASE = 'https://generativelanguage.googleapis.com/v1beta'

export function geminiConfigured(): boolean {
  return Boolean(process.env.GEMINI_API_KEY)
}

interface GenerateOptions {
  systemInstruction?: string
  json?: boolean        // JSON горимоор хариулахыг хүсэх
  temperature?: number
  image?: { mimeType: string; base64: string }  // multimodal (vision) оролт
  timeoutMs?: number    // default 30s; зураг уншихад илүү их хугацаа хэрэгтэй
}

// data URL (data:image/png;base64,XXX) → {mimeType, base64}
export function parseDataUrl(dataUrl: string): { mimeType: string; base64: string } | null {
  const m = dataUrl.match(/^data:(.+?);base64,(.*)$/)
  return m ? { mimeType: m[1], base64: m[2] } : null
}

// String literal доторх escape хийгдээгүй control тэмдэгт (raw newline/tab) JSON parse-г эвддэг.
// Бүтцийн whitespace-ийг space-ээр солих нь JSON-д аюулгүй.
function stripControlChars(s: string): string {
  let out = ''
  for (let i = 0; i < s.length; i++) {
    const code = s.charCodeAt(i)
    out += code < 0x20 ? ' ' : s[i]
  }
  return out
}

/**
 * Gemini-д текст промпт илгээж хариу авна. server-only — key client рүү гарахгүй.
 * Алдаа гарвал Error шиднэ (дуудагч талд fallback хийнэ).
 */
export async function geminiGenerate(prompt: string, opts: GenerateOptions = {}): Promise<string> {
  const key = process.env.GEMINI_API_KEY
  if (!key) throw new Error('GEMINI_API_KEY тохируулагдаагүй')
  const model = process.env.GEMINI_MODEL || 'gemini-2.5-flash'

  const parts: Record<string, unknown>[] = [{ text: prompt }]
  if (opts.image) {
    parts.push({ inlineData: { mimeType: opts.image.mimeType, data: opts.image.base64 } })
  }

  const body: Record<string, unknown> = {
    contents: [{ parts }],
    generationConfig: {
      temperature: opts.temperature ?? 0.4,
      ...(opts.json ? { responseMimeType: 'application/json' } : {}),
    },
  }
  if (opts.systemInstruction) {
    body.systemInstruction = { parts: [{ text: opts.systemInstruction }] }
  }

  // 503 (overloaded) / 429 (rate limit) үед богино backoff-той дахин оролдох
  let res: Response | null = null
  for (let attempt = 0; attempt < 3; attempt++) {
    res = await fetch(`${API_BASE}/models/${model}:generateContent?key=${key}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(opts.timeoutMs ?? 30_000),
    })
    if (res.ok) break
    if (res.status === 503 || res.status === 429) {
      await new Promise((r) => setTimeout(r, 800 * (attempt + 1)))
      continue
    }
    break // бусад алдаанд retry хийхгүй
  }

  if (!res || !res.ok) {
    const text = res ? await res.text().catch(() => '') : ''
    throw new Error(`Gemini API алдаа ${res?.status ?? '?'}: ${text.slice(0, 200)}`)
  }

  const data = await res.json()
  const respParts = data?.candidates?.[0]?.content?.parts
  const text = Array.isArray(respParts) ? respParts.map((p: { text?: string }) => p.text ?? '').join('') : ''
  if (!text) throw new Error('Gemini хоосон хариу буцаалаа')
  return text
}

/** JSON хариу хүсэж, parse хийж буцаана. */
export async function geminiJSON<T>(prompt: string, opts: Omit<GenerateOptions, 'json'> = {}): Promise<T> {
  const raw = await geminiGenerate(prompt, { ...opts, json: true })
  // ```json ... ``` блок цэвэрлэх (хааяа гардаг) + control тэмдэгт арилгах
  const cleaned = stripControlChars(
    raw.replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/, '').trim()
  )
  try {
    return JSON.parse(cleaned) as T
  } catch {
    // Сүүлчийн оролдлого: эхний { ... сүүлчийн } хүртэлх хэсгийг таслаж parse
    const first = cleaned.indexOf('{')
    const last = cleaned.lastIndexOf('}')
    if (first !== -1 && last > first) {
      return JSON.parse(cleaned.slice(first, last + 1)) as T
    }
    throw new Error('Gemini JSON parse алдаа')
  }
}
