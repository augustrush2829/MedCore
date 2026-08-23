import 'server-only'
import fs from 'fs'
import { PATHS } from './sources'

// ---------------------------------------------------------------------------
// CSV туслах — энгийн, quote-той талбарыг зөв уншина
// ---------------------------------------------------------------------------
function parseCSV(text: string): string[][] {
  const rows: string[][] = []
  let cur: string[] = []
  let field = ''
  let inQuotes = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (inQuotes) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++ }
      else if (ch === '"') inQuotes = false
      else field += ch
    } else {
      if (ch === '"') inQuotes = true
      else if (ch === ',') { cur.push(field); field = '' }
      else if (ch === '\n') { cur.push(field); rows.push(cur); cur = []; field = '' }
      else if (ch === '\r') { /* skip */ }
      else field += ch
    }
  }
  if (field.length || cur.length) { cur.push(field); rows.push(cur) }
  return rows.filter(r => r.some(c => c.trim()))
}

const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, '_')

// ---------------------------------------------------------------------------
// Датасетуудыг нэг удаа уншиж кэшлэх
// ---------------------------------------------------------------------------
export interface DiseaseRecord {
  disease: string
  symptoms: Set<string>
}

interface Datasets {
  diseases: DiseaseRecord[]            // disease_symptoms.csv (304 мөр)
  symptomWeight: Map<string, number>   // symptom_severity.csv
  descriptions: Map<string, string>    // disease_descriptions.csv
  precautions: Map<string, string[]>   // disease_precautions.csv
  edoctor: Record<string, string>[]    // edoctor_clean.json (219)
  icdIndex: Record<string, string>     // icd_index.json (8,896)
}

let _cache: Datasets | null = null

export function getDatasets(): Datasets {
  if (_cache) return _cache

  // 1. disease_symptoms
  const dsRows = parseCSV(fs.readFileSync(PATHS.diseaseSymptoms, 'utf-8'))
  const diseases: DiseaseRecord[] = dsRows.slice(1).map(cols => ({
    disease: cols[0].trim(),
    symptoms: new Set(cols.slice(1).map(norm).filter(Boolean)),
  }))

  // 2. symptom_severity
  const svRows = parseCSV(fs.readFileSync(PATHS.symptomSeverity, 'utf-8'))
  const symptomWeight = new Map<string, number>()
  svRows.slice(1).forEach(([sym, w]) => {
    if (sym) symptomWeight.set(norm(sym), Number(w) || 1)
  })

  // 3. descriptions
  const dRows = parseCSV(fs.readFileSync(PATHS.diseaseDescriptions, 'utf-8'))
  const descriptions = new Map<string, string>()
  dRows.slice(1).forEach(([dis, desc]) => { if (dis) descriptions.set(dis.trim(), desc?.trim() ?? '') })

  // 4. precautions
  const pRows = parseCSV(fs.readFileSync(PATHS.diseasePrecautions, 'utf-8'))
  const precautions = new Map<string, string[]>()
  pRows.slice(1).forEach(cols => {
    if (cols[0]) precautions.set(cols[0].trim(), cols.slice(1).map(c => c.trim()).filter(Boolean))
  })

  // 5. edoctor + 6. ICD
  const edoctor = JSON.parse(fs.readFileSync(PATHS.edoctor, 'utf-8'))
  const icdIndex = JSON.parse(fs.readFileSync(PATHS.icdIndex, 'utf-8'))

  _cache = { diseases, symptomWeight, descriptions, precautions, edoctor, icdIndex }
  return _cache
}

// ---------------------------------------------------------------------------
// Бүх ялгаатай симптомын жагсаалт (UI-ийн autocomplete-д)
// ---------------------------------------------------------------------------
export function allSymptoms(): { name: string; weight: number }[] {
  const { symptomWeight } = getDatasets()
  return [...symptomWeight.entries()]
    .map(([name, weight]) => ({ name, weight }))
    .sort((a, b) => a.name.localeCompare(b.name))
}
