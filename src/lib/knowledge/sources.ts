import path from 'path'

// Бүх dataset нь төслийн `data/` хавтаст багцлагдсан тул deploy дээр ажиллана.
const DATA_DIR = path.join(process.cwd(), 'data')

export const PATHS = {
  diseaseSymptoms: path.join(DATA_DIR, 'en_symptom_dataset', 'disease_symptoms.csv'),
  symptomSeverity: path.join(DATA_DIR, 'en_symptom_dataset', 'symptom_severity.csv'),
  diseaseDescriptions: path.join(DATA_DIR, 'en_symptom_dataset', 'disease_descriptions.csv'),
  diseasePrecautions: path.join(DATA_DIR, 'en_symptom_dataset', 'disease_precautions.csv'),
  edoctor: path.join(DATA_DIR, 'mn_edoctor_kb', 'edoctor_clean.json'),
  icdIndex: path.join(DATA_DIR, 'icd', 'icd_index.json'),
}

export const KNOWLEDGE_SOURCES = [
  {
    id: 'en-disease-symptoms',
    title: 'Disease–Symptom Dataset (Kaggle, 41 өвчин)',
    file: PATHS.diseaseSymptoms,
    type: 'csv' as const,
    language: 'en',
    tags: ['symptoms', 'differential-diagnosis'],
  },
  {
    id: 'mn-edoctor-kb',
    title: 'edoctor.mn — Монгол эмнэлзүйн мэдлэгийн сан (219 өвчин)',
    file: PATHS.edoctor,
    type: 'json' as const,
    language: 'mn',
    tags: ['mongolian', 'clinical', 'rag'],
  },
  {
    id: 'icd-mn',
    title: 'ICD Монгол нэршил (8,896 код)',
    file: PATHS.icdIndex,
    type: 'icd' as const,
    language: 'mn',
    version: '2026',
    tags: ['ICD', 'diagnosis', 'classification'],
  },
]
