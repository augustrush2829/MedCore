import type { Patient, ClinicalCase, AIResponse } from '@/types'

export const currentUser = {
  id: 'current-user',
  name: 'Эмч',
  email: '',
  role: 'doctor' as const,
  organization: '',
  specialty: 'Clinical user',
}

export const seedPatients: Patient[] = [
  { id: 'p1', name: 'Б. Энхжаргал', age: 45, gender: 'female', medicalRecordNo: 'MR-2024-001', dateOfBirth: '1979-03-15', phone: '+976 9911-2233', lastVisit: '2026-05-20' },
  { id: 'p2', name: 'Д. Батсүх', age: 62, gender: 'male', medicalRecordNo: 'MR-2024-002', dateOfBirth: '1962-07-08', phone: '+976 9922-4455', lastVisit: '2026-05-28' },
  { id: 'p3', name: 'Н. Оюунчимэг', age: 33, gender: 'female', medicalRecordNo: 'MR-2024-003', dateOfBirth: '1991-11-22', phone: '+976 9933-6677', lastVisit: '2026-05-29' },
  { id: 'p4', name: 'Г. Мөнхбаатар', age: 55, gender: 'male', medicalRecordNo: 'MR-2024-004', dateOfBirth: '1969-02-10', phone: '+976 9944-8899', lastVisit: '2026-05-30' },
  { id: 'p5', name: 'С. Сарнай', age: 28, gender: 'female', medicalRecordNo: 'MR-2024-005', dateOfBirth: '1998-06-05', phone: '+976 9955-0011', lastVisit: '2026-04-15' },
]

export const seedAIResponse: AIResponse = {
  id: 'ai1',
  clinicalSummary: '45 настай эмэгтэй өвчтөн 3 хоногийн турш баруун дээд хэвлийн өвдөлт, дотор муухайрах, давалгааных шинж тэмдэгтэй ирсэн. ALT/AST үзүүлэлт хэвийн дээд хязгаараас 2-3 дахин өссөн байна. Өвчтөн Atorvastatin (40мг) 6 сарын турш хэрэглэж байна.',
  differentialDiagnosis: [
    {
      name: 'Эмийн гаж нөлөөнөөс үүдсэн элэгний гэмтэл (DILI)',
      confidence: 72,
      icdCode: 'K71.2',
      supportingEvidence: ['ALT/AST хэвийн дээд хязгаараас 2-3 дахин өссөн', 'Atorvastatin хэрэглэж эхэлснээс хойш 6 сар болсон', 'Баруун дээд хэвлийн өвдөлт'],
      missingEvidence: ['Элэгний хатуурал шалгах ultrasound', 'ANA, AMA шинжилгээ', 'Архины хэрэглээний дэлгэрэнгүй түүх'],
    },
    {
      name: 'Цөсний чулуу (Cholelithiasis)',
      confidence: 58,
      icdCode: 'K80.2',
      supportingEvidence: ['Баруун дээд хэвлийн өвдөлт', '45 настай эмэгтэй (эрсдэлт бүлэг)', 'Дотор муухайрах'],
      missingEvidence: ['Абдоминал ultrasound', 'Шарлалт байгаа эсэх шалгаагүй', 'Өвдөлт идэж уусны дараа нэмэгдэх эсэх'],
    },
    {
      name: 'Архаг вирусын гепатит',
      confidence: 25,
      icdCode: 'B18.1',
      supportingEvidence: ['ALT/AST өсөлт'],
      missingEvidence: ['HBsAg, Anti-HCV шинжилгээ хийгдээгүй', 'Вирусын дарамтын шинжилгээ байхгүй'],
    },
  ],
  missingInformation: [
    'Абдоминал ultrasound хийгдээгүй',
    'HBsAg, Anti-HCV серологийн шинжилгээ дутуу',
    'Atorvastatin эхэлсэнтэй холбоотой шинжилгээний baseline ALT/AST байхгүй',
    'Архины хэрэглээний дэлгэрэнгүй түүх авагдаагүй',
  ],
  recommendedTests: [
    { name: 'Абдоминал ultrasound', reason: 'Элэгний бүтэц, цөсний чулуу, цөсний сувгийн өргөсөлт шалгах', priority: 'urgent' },
    { name: 'HBsAg, Anti-HCV', reason: 'Вирусын гепатит үгүйсгэх', priority: 'urgent' },
    { name: 'GGT, ALP', reason: 'Цөсний замын гэмтэл тодорхойлох', priority: 'routine' },
    { name: 'Protrombin time (PT/INR)', reason: 'Элэгний синтетик функц үнэлэх', priority: 'routine' },
    { name: 'ANA, AMA (хэрэв DILI батлагдахгүй бол)', reason: 'Аутоиммун гепатит үгүйсгэх', priority: 'routine' },
  ],
  medicationWarnings: [
    {
      type: 'dose_risk',
      severity: 'high',
      description: 'Atorvastatin нь hepatotoxicity үүсгэх мэдэгдсэн гаж нөлөөтэй. ALT/AST 3 дахин дээш өссөн тохиолдолд эмийг зогсоох шаардлагатай.',
      medications: ['Atorvastatin 40мг'],
    },
  ],
  causalityAssessment: {
    type: 'medication_related',
    confidence: 65,
    evidence: 'ALT/AST өсөлт нь Atorvastatin эхэлсний дараа илэрч байна. RUCAM scale дагуу "probable" ангилалд хамрагдана. Гэсэн ч бусад шалтгааныг үгүйсгэх шинжилгээ дутуу байна.',
  },
  redFlags: [
    'Шарлалт илэрвэл яаралтай эмнэлэгт ирүүлэх шаардлагатай',
    'PT/INR өсвөл хурдан улирч буй элэгний дутагдлын шинж байж болно',
  ],
  citations: [
    { title: 'Drug-Induced Liver Injury (DILI) — EASL Clinical Practice Guidelines 2019', source: 'EASL', version: '2019', url: '' },
    { title: 'Statin Safety and Associated Adverse Events', source: 'ACC/AHA 2022', version: '2022', url: '' },
    { title: 'ACG Clinical Guideline: Evaluation of Abnormal Liver Chemistries', source: 'ACG', version: '2023', url: '' },
  ],
  confidenceLevel: 68,
  doctorConfirmationRequired: true,
}

export const seedCases: ClinicalCase[] = [
  {
    id: 'c1',
    patientId: 'p1',
    patientName: 'Б. Энхжаргал',
    chiefComplaint: 'Хэвлийн өвдөлт, дотор муухайрах',
    status: 'ai_complete',
    createdAt: '2026-05-31T09:00:00',
    updatedAt: '2026-05-31T09:30:00',
    hasRedFlag: false,
    symptoms: [
      { id: 's1', name: 'Баруун дээд хэвлийн өвдөлт', severity: 'moderate', onsetDate: '2026-05-28', duration: '3 хоног', note: 'Идсэний дараа нэмэгддэг' },
      { id: 's2', name: 'Дотор муухайрах', severity: 'mild', onsetDate: '2026-05-28', duration: '3 хоног' },
    ],
    labResults: [
      { id: 'l1', testName: 'ALT', value: 120, unit: 'U/L', referenceRangeLow: 7, referenceRangeHigh: 40, abnormalFlag: true, collectedAt: '2026-05-31' },
      { id: 'l2', testName: 'AST', value: 98, unit: 'U/L', referenceRangeLow: 10, referenceRangeHigh: 35, abnormalFlag: true, collectedAt: '2026-05-31' },
      { id: 'l3', testName: 'Билирубин нийт', value: 1.1, unit: 'mg/dL', referenceRangeLow: 0.2, referenceRangeHigh: 1.2, abnormalFlag: false, collectedAt: '2026-05-31' },
    ],
    medications: [
      { id: 'm1', name: 'Atorvastatin', dose: '40мг', route: 'амаар', frequency: 'Өдөрт 1 удаа', startDate: '2025-11-15', ingredients: ['Atorvastatin calcium'], status: 'active' },
      { id: 'm2', name: 'Metformin', dose: '500мг', route: 'амаар', frequency: 'Өдөрт 2 удаа', startDate: '2024-01-10', ingredients: ['Metformin hydrochloride'], status: 'active' },
    ],
    aiResponse: seedAIResponse,
  },
  {
    id: 'c2',
    patientId: 'p2',
    patientName: 'Д. Батсүх',
    chiefComplaint: 'Цээжний өвдөлт, амьсгал давчдах',
    status: 'ai_pending',
    createdAt: '2026-05-31T10:15:00',
    updatedAt: '2026-05-31T10:15:00',
    hasRedFlag: true,
    symptoms: [
      { id: 's3', name: 'Цээжний өвдөлт', severity: 'severe', onsetDate: '2026-05-31', duration: '2 цаг', note: 'Зүүн гарт цацардаг' },
    ],
    labResults: [],
    medications: [],
  },
  {
    id: 'c3',
    patientId: 'p3',
    patientName: 'Н. Оюунчимэг',
    chiefComplaint: 'Толгой өвдөх, халуурах',
    status: 'draft',
    createdAt: '2026-05-31T11:00:00',
    updatedAt: '2026-05-31T11:00:00',
    hasRedFlag: false,
    symptoms: [],
    labResults: [],
    medications: [],
  },
]
