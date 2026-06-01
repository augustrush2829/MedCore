import type { StoredExplanation } from './patient-store'

// StoredExplanation → frontend PatientExplanation shape (patient-api.ts-тэй тааруулна)
export function toApiExplanation(e: StoredExplanation) {
  return {
    id: e.id,
    patient_id: e.patient_id,
    diagnosis_text: e.diagnosis_text,
    lab_name: e.lab_name,
    lab_value: e.lab_value,
    lab_unit: e.lab_unit,
    reference_range: e.reference_range,
    lab_collected_at: e.lab_collected_at,
    attachment_name: e.attachment_name,
    attachment_content_type: e.attachment_content_type,
    attachment_data_url: null, // зураг тусдаа endpoint-оор (жинг хөнгөн байлгах)
    attachment_object_key: null,
    attachment_sha256: null,
    attachment_size_bytes: e.attachment_data_url ? e.attachment_data_url.length : null,
    attachment_width: null,
    attachment_height: null,
    has_attachment: Boolean(e.attachment_data_url),
    extracted_lab_data: {
      status: e.extracted.status,
      model: e.extracted.model,
      image_sha256: null,
      image_content_type: e.attachment_content_type,
      image_size_bytes: e.attachment_data_url ? e.attachment_data_url.length : null,
      image_width: null,
      image_height: null,
      ocr_engine: e.extracted.ocr_text ? 'gemini-vision' : null,
      ocr_languages: e.extracted.ocr_text ? 'mn+en' : null,
      ocr_text: e.extracted.ocr_text,
      observations: e.extracted.observations,
      notes: e.extracted.notes,
    },
    extraction_status: e.extracted.status,
    extraction_model: e.extracted.model,
    patient_question: e.patient_question,
    content: e.content,
    safety_status: e.safety_status,
    created_at: e.created_at,
  }
}
