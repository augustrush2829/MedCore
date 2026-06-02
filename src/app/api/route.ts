import { NextResponse } from 'next/server'

const docs = {
  name: 'MedCore API',
  version: 'mvp-v2',
  description: 'Frontend BFF API. Case analyze нь local rule engine биш, backend FastAPI AI endpoint рүү sync хийж ажиллана.',
  environment: {
    backendBaseUrl: 'MEDCORE_BACKEND_URL, default http://localhost:8000',
    backendLogin: 'POST /api/auth/login нь backend /auth/login proxy хийж medcore.staff.token cookie хадгална',
    backendDocs: 'FastAPI running үед http://localhost:8000/docs',
  },
  flows: [
    {
      name: 'AI analyze',
      trigger: 'POST /api/cases/{id}/analyze',
      steps: [
        'Local case болон patient data уншина',
        'Backend-д patient байхгүй бол /patients API-аар үүсгэнэ',
        'Backend-д шинэ case үүсгэнэ',
        'Symptoms, labs, medications, allergies, attachments-г backend API руу sync хийнэ',
        'Login хийсэн doctor-ийн backend JWT cookie-г ашиглана',
        'Backend /cases/{case_id}/ai/differential-diagnosis дуудна',
        'Backend AIContent response-г UI-ийн AIResponse shape рүү map хийнэ',
      ],
    },
    {
      name: 'Image and lab storage',
      trigger: 'Case attachment эсвэл patient portal upload',
      steps: [
        'Файлын bytes DB-д шууд хадгалахгүй',
        'backend/storage/patient_uploads доор encrypted object file хадгална',
        'DB-д object_key, content_type, sha256, size_bytes, width, height metadata хадгална',
        'OCR/extraction result нь JSON байдлаар document_extractions эсвэл patient_portal_explanations.extracted_lab_data-д хадгалагдана',
      ],
    },
  ],
  endpoints: [
    {
      group: 'Auth',
      routes: [
        { method: 'POST', path: '/api/auth/login', description: 'Backend /auth/login proxy. Амжилттай бол medcore.staff.token httpOnly cookie тавина.', body: { email: 'string', password: 'string' } },
        { method: 'POST', path: '/api/auth/logout', description: 'Staff login cookie устгана.' },
        { method: 'GET', path: '/api/auth/status', description: 'Backend available эсэх, staff authenticated эсэхийг шалгана.' },
      ],
    },
    {
      group: 'Dashboard',
      routes: [
        { method: 'GET', path: '/api/dashboard', description: 'Dashboard stats болон recent cases.' },
      ],
    },
    {
      group: 'Patients',
      routes: [
        { method: 'GET', path: '/api/patients', description: 'Өвчтөнүүдийн жагсаалт.' },
        { method: 'POST', path: '/api/patients', description: 'Шинэ өвчтөн үүсгэнэ.', body: { name: 'string', dateOfBirth: 'YYYY-MM-DD', gender: 'male|female|other', phone: 'string?' } },
        { method: 'GET', path: '/api/patients/{id}', description: 'Өвчтөн, cases, patient labs уншина.' },
        { method: 'GET', path: '/api/patients/{id}/labs', description: 'Өвчтөний lab history.' },
        { method: 'POST', path: '/api/patients/{id}/labs', description: 'Patient lab мөрүүд нэмнэ.', body: { labs: 'LabResult[]' } },
      ],
    },
    {
      group: 'Cases',
      routes: [
        { method: 'GET', path: '/api/cases', description: 'Case жагсаалт.' },
        { method: 'POST', path: '/api/cases', description: 'Patient дээр шинэ case үүсгэнэ.', body: { patientId: 'string', chiefComplaint: 'string' } },
        { method: 'GET', path: '/api/cases/{id}', description: 'Case detail уншина.' },
        { method: 'PUT', path: '/api/cases/{id}', description: 'Case structured data update.' },
        { method: 'DELETE', path: '/api/cases/{id}', description: 'Case устгана.' },
        { method: 'POST', path: '/api/cases/{id}/analyze', description: 'Backend FastAPI AI analyze ажиллуулна. Local rule engine ашиглахгүй.' },
        { method: 'POST', path: '/api/cases/{id}/decision', description: 'Эмчийн accept/edit/reject decision хадгална.', body: { decision: 'accept|edit|reject', finalNote: 'string?' } },
        { method: 'POST', path: '/api/cases/{id}/extract-labs', description: 'Case lab attachment image-ээс Gemini-р structured lab уншиж case.labResults руу нэмнэ.' },
      ],
    },
    {
      group: 'Knowledge and diagnosis',
      routes: [
        { method: 'GET', path: '/api/knowledge?symptoms', description: 'Autocomplete-д ашиглах symptom list.' },
        { method: 'GET', path: '/api/knowledge', description: 'Knowledge dataset metadata.' },
        { method: 'POST', path: '/api/diagnosis', description: 'Dataset-based symptom differential diagnosis.', body: { symptoms: 'string[]' } },
      ],
    },
    {
      group: 'Patient portal',
      routes: [
        { method: 'POST', path: '/api/patient-portal/login', description: 'Patient portal login token авна.' },
        { method: 'GET', path: '/api/patient-portal/explanations', description: 'Patient explanation history.' },
        { method: 'POST', path: '/api/patient-portal/explanations', description: 'Diagnosis/lab/image оруулаад patient-facing explanation үүсгэнэ.' },
        { method: 'GET', path: '/api/patient-portal/explanations/{id}/image', description: 'Patient portal explanation attachment image уншина.' },
      ],
    },
    {
      group: 'Admin and audit',
      routes: [
        { method: 'GET', path: '/api/admin', description: 'Admin overview.' },
        { method: 'POST', path: '/api/admin/hospitals', description: 'Hospital үүсгэнэ.' },
        { method: 'PATCH', path: '/api/admin/hospitals/{id}', description: 'Hospital active/disabled toggle.' },
        { method: 'POST', path: '/api/admin/users', description: 'Admin user үүсгэнэ.' },
        { method: 'PATCH', path: '/api/admin/users/{id}', description: 'User active/disabled toggle.' },
        { method: 'PATCH', path: '/api/admin/uploads/{id}/review', description: 'Upload review-г processed болгоно.' },
        { method: 'GET', path: '/api/audit', description: 'Audit event list.' },
      ],
    },
  ],
  backendStorageTables: [
    {
      table: 'case_attachments',
      purpose: 'Doctor case attachment metadata',
      columns: ['section', 'file_name', 'content_type', 'object_key', 'sha256', 'size_bytes', 'width', 'height', 'extraction_status'],
    },
    {
      table: 'document_extractions',
      purpose: 'Attachment OCR/Gemini extraction output',
      columns: ['raw_text', 'result_json', 'notes', 'status', 'model'],
    },
    {
      table: 'proposed_clinical_facts',
      purpose: 'Doctor review хийх proposed lab/medication/allergy/symptom facts',
      columns: ['fact_type', 'fact_json', 'source_text', 'confidence', 'status'],
    },
    {
      table: 'patient_portal_explanations',
      purpose: 'Patient portal lab image/explanation metadata and extraction JSON',
      columns: ['attachment_object_key', 'attachment_sha256', 'attachment_size_bytes', 'extracted_lab_data', 'extraction_status', 'explanation_json'],
    },
  ],
}

function htmlEscape(value: string) {
  return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
}

function renderHtml() {
  const endpointGroups = docs.endpoints.map((group) => `
    <section>
      <h2>${htmlEscape(group.group)}</h2>
      <div class="routes">
        ${group.routes.map((route) => `
          <article class="route">
            <span class="method">${route.method}</span>
            <code>${htmlEscape(route.path)}</code>
            <p>${htmlEscape(route.description)}</p>
            ${'body' in route && route.body ? `<pre>${htmlEscape(JSON.stringify(route.body, null, 2))}</pre>` : ''}
          </article>
        `).join('')}
      </div>
    </section>
  `).join('')

  const flows = docs.flows.map((flow) => `
    <section>
      <h2>${htmlEscape(flow.name)}</h2>
      <p><b>Trigger:</b> <code>${htmlEscape(flow.trigger)}</code></p>
      <ol>${flow.steps.map((step) => `<li>${htmlEscape(step)}</li>`).join('')}</ol>
    </section>
  `).join('')

  const tables = docs.backendStorageTables.map((table) => `
    <article class="route">
      <code>${htmlEscape(table.table)}</code>
      <p>${htmlEscape(table.purpose)}</p>
      <pre>${htmlEscape(table.columns.join(', '))}</pre>
    </article>
  `).join('')

  return `<!doctype html>
<html lang="mn">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${htmlEscape(docs.name)}</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f8fafc; color: #0f172a; }
    main { max-width: 1040px; margin: 0 auto; padding: 32px 20px 56px; }
    header { margin-bottom: 28px; }
    h1 { margin: 0 0 8px; font-size: 30px; }
    h2 { margin: 28px 0 12px; font-size: 18px; }
    p, li { color: #475569; line-height: 1.55; }
    .meta, .route { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; }
    .routes { display: grid; gap: 10px; }
    .method { display: inline-block; min-width: 58px; font-weight: 700; color: #2563eb; }
    code { color: #0f172a; font-weight: 700; }
    pre { overflow: auto; background: #f1f5f9; border-radius: 6px; padding: 10px; color: #334155; }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>${htmlEscape(docs.name)}</h1>
      <p>${htmlEscape(docs.description)}</p>
      <div class="meta">
        <p><b>Version:</b> ${htmlEscape(docs.version)}</p>
        <p><b>Backend:</b> ${htmlEscape(docs.environment.backendBaseUrl)}</p>
        <p><b>JSON:</b> <a href="/api?format=json">/api?format=json</a></p>
      </div>
    </header>
    ${flows}
    ${endpointGroups}
    <section>
      <h2>Backend Storage Tables</h2>
      <div class="routes">${tables}</div>
    </section>
  </main>
</body>
</html>`
}

export async function GET(req: Request) {
  const url = new URL(req.url)
  const wantsJson = url.searchParams.get('format') === 'json' || req.headers.get('accept')?.includes('application/json')

  if (wantsJson) {
    return NextResponse.json(docs)
  }

  return new Response(renderHtml(), {
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  })
}
