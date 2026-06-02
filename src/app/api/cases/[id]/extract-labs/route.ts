import { NextResponse } from 'next/server'
import { extractLabResultsFromImage } from '@/lib/ai/lab-image-extractor'
import { addPatientLabs, getCase, updateCase } from '@/lib/clinical-store'
import type { LabResult } from '@/types'

function labKey(lab: LabResult) {
  return `${lab.testName.toLowerCase()}::${lab.collectedAt}`
}

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const clinicalCase = getCase(id)
  if (!clinicalCase) return NextResponse.json({ error: 'Тохиолдол олдсонгүй' }, { status: 404 })

  const labImages = (clinicalCase.attachments ?? []).filter((attachment) => attachment.section === 'labs')
  if (labImages.length === 0) {
    return NextResponse.json({ error: 'Лабораторийн зураг хавсаргаагүй байна' }, { status: 400 })
  }

  try {
    const extracted = (
      await Promise.all(
        labImages.map((attachment) =>
          extractLabResultsFromImage(attachment.dataUrl)
        )
      )
    ).flat()

    const existing = new Set((clinicalCase.labResults ?? []).map(labKey))
    const newLabs = extracted.filter((lab) => !existing.has(labKey(lab)))
    const updated = updateCase(id, { labResults: [...clinicalCase.labResults, ...newLabs] })
    const patientLabs = addPatientLabs(clinicalCase.patientId, newLabs, {
      caseId: id,
      source: 'image_ocr',
      sourceAttachmentId: labImages[0]?.id,
    })

    return NextResponse.json({
      added: newLabs.length,
      extracted: extracted.length,
      patientLabsAdded: patientLabs.length,
      case: updated,
    })
  } catch (caught) {
    const message = caught instanceof Error ? caught.message : 'Зурагнаас lab уншихад алдаа гарлаа'
    return NextResponse.json({ error: message }, { status: 422 })
  }
}
