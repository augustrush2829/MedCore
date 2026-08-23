import 'server-only'
import { getDatasets } from './datasets'

export interface DiagnosisMatch {
  disease: string
  score: number            // 0–100 (жинлэсэн давхцлын хувь)
  matchedSymptoms: string[]
  description: string
  precautions: string[]
  icdCode?: string
  icdName?: string
  edoctorMatch?: { name: string; url: string; treatment: string }
}

const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, '_')

// edoctor.mn-аас англи өвчний нэрэнд ойролцоо монгол бичлэг хайх (энгийн keyword)
function findEdoctor(disease: string) {
  const { edoctor } = getDatasets()
  const key = disease.toLowerCase()
  const hit = edoctor.find(r => {
    const name = (r['Өвчин'] ?? '').toLowerCase()
    return name.includes(key) || key.includes(name)
  })
  if (!hit) return undefined
  return {
    name: hit['Өвчин'] ?? '',
    url: hit['URL'] ?? '',
    treatment: (hit['Эмчилгээ'] ?? '').slice(0, 300),
  }
}

// ICD индексээс англи нэрээр ойролцоо код хайх
function findICD(disease: string) {
  const { icdIndex } = getDatasets()
  const key = disease.toLowerCase()
  for (const [code, name] of Object.entries(icdIndex)) {
    if (name.toLowerCase().includes(key)) return { code, name }
  }
  return undefined
}

/**
 * Симптомын жагсаалтаас differential diagnosis гаргана.
 * Оноо = (таарсан симптомын жингийн нийлбэр) / (өвчний бүх симптомын жингийн нийлбэр)
 */
export function runDifferentialDiagnosis(inputSymptoms: string[], topN = 5): DiagnosisMatch[] {
  const { diseases, symptomWeight, descriptions, precautions } = getDatasets()
  const input = new Set(inputSymptoms.map(norm).filter(Boolean))
  if (input.size === 0) return []

  const weightOf = (s: string) => symptomWeight.get(s) ?? 1

  const scored = diseases.map(d => {
    let matchWeight = 0
    let totalWeight = 0
    const matched: string[] = []
    for (const sym of d.symptoms) {
      const w = weightOf(sym)
      totalWeight += w
      if (input.has(sym)) { matchWeight += w; matched.push(sym) }
    }
    // input-ийн талаас coverage-ийг бас тооцож хэт ерөнхий оношийг бууруулна
    const inputCoverage = matched.length / input.size
    const diseaseCoverage = totalWeight ? matchWeight / totalWeight : 0
    const score = Math.round((0.6 * diseaseCoverage + 0.4 * inputCoverage) * 100)
    return { disease: d.disease, score, matched }
  })

  // Хамгийн өндөр оноотой ялгаатай өвчнүүдийг авах
  const byDisease = new Map<string, { score: number; matched: string[] }>()
  for (const s of scored) {
    const cur = byDisease.get(s.disease)
    if (!cur || s.score > cur.score) byDisease.set(s.disease, { score: s.score, matched: s.matched })
  }

  return [...byDisease.entries()]
    .map(([disease, { score, matched }]) => ({
      disease,
      score,
      matchedSymptoms: matched,
      description: descriptions.get(disease) ?? '',
      precautions: precautions.get(disease) ?? [],
      ...(() => { const icd = findICD(disease); return icd ? { icdCode: icd.code, icdName: icd.name } : {} })(),
      edoctorMatch: findEdoctor(disease),
    }))
    .filter(m => m.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, topN)
}
