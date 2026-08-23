import base64
import re
import subprocess
import tempfile

from app.core.config import get_settings
from app.schemas import ImageExtractionResult, PatientExplanationContent, PatientExplanationCreate
from app.services.gemini import generate_json
from app.services.image_storage import StoredImage, extension_for_content_type, read_patient_image


EXTRACTION_MODEL = "medcore-image-extraction-local-v1"


def build_patient_explanation(payload: PatientExplanationCreate) -> PatientExplanationContent:
    diagnosis = clean(payload.diagnosis_text)
    lab_name = clean(payload.lab_name)
    lab_value = clean(payload.lab_value)
    lab_unit = clean(payload.lab_unit)
    reference_range = clean(payload.reference_range)
    patient_question = clean(payload.patient_question)
    status_kind, status_text = interpret_lab_status(lab_value, reference_range)

    summary = (
        f"Таны оруулсан онош: {diagnosis}. Энэ тайлбар нь оношийг батлахгүй, ойлгоход туслах зорилготой."
        if diagnosis
        else "Онош бичигдээгүй байна. Шинжилгээний хариуг онош, зовиур, хэрэглэж буй эмтэй хамт ойлгоно."
    )
    lab_meaning = (
        f"{lab_name} шинжилгээний утга {lab_value or 'оруулгагүй'} {lab_unit}. {status_text}"
        if lab_name
        else "Шинжилгээний нэр бичигдээгүй байна. Жишээ нь ALT, AST, HbA1c, CRP, гемоглобин гэх мэтээр оруулна."
    )

    return PatientExplanationContent(
        summary=summary,
        lab_meaning=lab_meaning,
        plain_language=plain_language_points(diagnosis, lab_name, status_kind),
        next_questions=next_questions(diagnosis, lab_name, patient_question),
        safety_notes=safety_notes(diagnosis, lab_name, status_kind),
        disclaimer="Энэ нь өвчтөнд зориулсан ойлгомжтой тайлбар бөгөөд эмчийн үзлэг, онош, эмчилгээний шийдвэрийг орлохгүй.",
    )


def process_lab_image(payload: PatientExplanationCreate, stored_image: StoredImage | None) -> ImageExtractionResult:
    if stored_image is None:
        return ImageExtractionResult(
            status="not_requested",
            model=EXTRACTION_MODEL,
            notes=["Зураг ирээгүй тул image AI extraction ажиллаагүй."],
        )

    observations, ocr_text, extraction_notes = run_local_vision_lab_extraction(stored_image)
    ocr_engine = "local_vision"
    ocr_languages = None
    if not observations:
        fallback_text, fallback_notes = run_tesseract_ocr(stored_image)
        observations = extract_observations_from_ocr(fallback_text)
        ocr_text = ocr_text or fallback_text
        extraction_notes.extend(["Local vision model structured extraction хоосон байсан тул Tesseract fallback ажиллуулсан.", *fallback_notes])
        ocr_engine = "local_vision+tesseract"
        ocr_languages = get_settings().tesseract_languages

    fallback_observation = build_observation_from_payload(payload)
    if not observations and fallback_observation is not None:
        observations = [fallback_observation]
    notes = [
        "Зураг file/object storage-д хадгалагдаж, database-д object key/hash/metadata хадгалагдсан.",
        "Local vision model structured OCR эхэлж ажиллаж, raw text болон lab мөрүүдийг extraction JSON-д хадгалсан.",
        *extraction_notes,
    ]
    low_confidence = any(int(observation.get("confidence") or 0) < 70 for observation in observations)
    if not observations:
        notes.append("Зургаас lab мөрийг автоматаар баталгаатай уншаагүй тул хүний review шаардлагатай.")
        status = "requires_review"
    elif low_confidence:
        notes.append("Зарим lab мөрийн confidence 70%-аас бага тул хүний review шаардлагатай.")
        status = "requires_review"
    else:
        notes.append("OCR/form extraction result-ийг structured observation болгон normalize хийж хадгалсан.")
        status = "processed"

    return ImageExtractionResult(
        status=status,
        model=EXTRACTION_MODEL,
        image_sha256=stored_image.sha256,
        image_content_type=stored_image.content_type,
        image_size_bytes=stored_image.size_bytes,
        image_width=stored_image.width,
        image_height=stored_image.height,
        ocr_engine=ocr_engine,
        ocr_languages=ocr_languages,
        ocr_text=ocr_text or None,
        observations=observations,
        notes=notes,
    )


def clean(value: str | None) -> str:
    return value.strip() if value else ""


def build_observation_from_payload(payload: PatientExplanationCreate):
    lab_name = clean(payload.lab_name)
    if not lab_name:
        return None
    status_kind, _ = interpret_lab_status(clean(payload.lab_value), clean(payload.reference_range))
    abnormal_flag = None if status_kind == "unknown" else status_kind in {"high", "low"}
    return {
        "test_name": lab_name,
        "value": clean(payload.lab_value) or None,
        "unit": clean(payload.lab_unit) or None,
        "reference_range": clean(payload.reference_range) or None,
        "abnormal_flag": abnormal_flag,
        "source": "patient_form_fallback",
        "confidence": 55 if payload.attachment_data_url else 45,
    }


def run_local_vision_lab_extraction(stored_image: StoredImage) -> tuple[list[dict], str, list[str]]:
    image_bytes = read_patient_image(stored_image.object_key)
    prompt = """
Extract laboratory result table rows from this image.

Return JSON only with this exact shape:
{
  "ocr_text": "compact plain text transcription",
  "observations": [
    {
      "test_name": "ALT",
      "value": "48",
      "unit": "U/L",
      "reference_range": "7 - 40",
      "abnormal_flag": true,
      "source": "local_vision",
      "confidence": 95
    }
  ],
  "notes": []
}

Rules:
- Extract table test rows only. Do not extract patient identifiers or headings as observations.
- Preserve decimal points exactly. Use medical/table context before deciding between 11.8 and 118, 84.2 and 842, 4.2 and 42, 0.8 and 08.
- Normalize common units to: U/L, mg/dL, g/dL, mmol/L, %, fL, pg, x10^9/L, x10^12/L, mL/min/1.73m2.
- Preserve comparison signs in reference ranges, for example <200, <100, >40.
- abnormal_flag must be true for High/Low rows, false for Normal rows, null only if unclear.
- confidence must be an integer 0-100. Lower it when the image is blurry or the row is ambiguous.
"""
    try:
        result = generate_json(
            prompt,
            system_instruction=(
                "You are a careful medical-lab OCR extraction engine for a healthcare app. "
                "The image can be fictional test data. Return strict JSON, no prose."
            ),
            image={
                "mime_type": stored_image.content_type,
                "base64": base64.b64encode(image_bytes).decode("ascii"),
            },
            timeout_seconds=90,
        )
    except Exception as exc:
        return [], "", [f"Local vision OCR ажилласангүй: {exc}"]

    raw_observations = result.get("observations")
    observations = normalize_vision_observations(raw_observations if isinstance(raw_observations, list) else [])
    ocr_text = normalize_ocr_text(str(result.get("ocr_text") or ""))
    notes = result.get("notes") if isinstance(result.get("notes"), list) else []
    return observations, ocr_text, [f"Local vision structured rows: {len(observations)}", *[str(note) for note in notes[:5]]]


def normalize_vision_observations(raw_observations: list) -> list[dict]:
    observations: list[dict] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for raw in raw_observations:
        if not isinstance(raw, dict):
            continue
        test_name = clean_string(raw.get("test_name"))
        if not test_name:
            continue
        value = clean_string(raw.get("value"))
        unit = normalize_unit(clean_string(raw.get("unit")))
        reference_range = normalize_reference_range(clean_string(raw.get("reference_range")))
        key = (test_name.lower(), value, reference_range)
        if key in seen:
            continue
        seen.add(key)
        confidence = coerce_confidence(raw.get("confidence"))
        observations.append(
            {
                "test_name": test_name,
                "value": value,
                "unit": unit,
                "reference_range": reference_range,
                "abnormal_flag": coerce_abnormal(raw.get("abnormal_flag")),
                "source": "local_vision",
                "confidence": confidence,
            }
        )
    return observations


def clean_string(value) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def normalize_unit(value: str | None) -> str | None:
    if not value:
        return None
    compact = value.replace(" ", "")
    aliases = {
        "ил": "U/L",
        "u/l": "U/L",
        "ul": "U/L",
        "mg/dl": "mg/dL",
        "g/dl": "g/dL",
        "mmol/l": "mmol/L",
        "fl": "fL",
        "x10*9/l": "x10^9/L",
        "x10^9/l": "x10^9/L",
        "x10*12/l": "x10^12/L",
        "x10^12/l": "x10^12/L",
        "ml/min/1.73m2": "mL/min/1.73m2",
    }
    return aliases.get(compact.lower(), value)


def normalize_reference_range(value: str | None) -> str | None:
    if not value:
        return None
    return (
        value.replace("–", "-")
        .replace("—", "-")
        .replace("«", "<")
        .replace("≤", "<=")
        .replace("≥", ">=")
        .replace(",", ".")
        .strip()
    )


def coerce_confidence(value) -> int:
    try:
        confidence = int(round(float(value)))
    except (TypeError, ValueError):
        confidence = 70
    return max(0, min(100, confidence))


def coerce_abnormal(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered in {"true", "yes", "high", "low", "abnormal", "1"}:
        return True
    if lowered in {"false", "no", "normal", "0"}:
        return False
    return None


def run_tesseract_ocr(stored_image: StoredImage) -> tuple[str, list[str]]:
    image_bytes = read_patient_image(stored_image.object_key)
    suffix = extension_for_content_type(stored_image.content_type)
    with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
        temp_file.write(image_bytes)
        temp_file.flush()
        command = [
            "tesseract",
            temp_file.name,
            "stdout",
            "-l",
            get_settings().tesseract_languages,
            "--psm",
            "6",
        ]
        try:
            completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "", [f"Tesseract OCR ажилласангүй: {exc}"]
    if completed.returncode != 0:
        error = completed.stderr.strip() or "unknown tesseract error"
        return "", [f"Tesseract OCR алдаа: {error}"]
    text = normalize_ocr_text(completed.stdout)
    return text, [f"Tesseract OCR text length: {len(text)}"]


def normalize_ocr_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_observations_from_ocr(ocr_text: str) -> list[dict]:
    observations: list[dict] = []
    seen: set[tuple[str, str | None]] = set()
    for line in ocr_text.splitlines():
        observation = parse_lab_line(line)
        if not observation:
            continue
        key = (observation["test_name"], observation["value"])
        if key in seen:
            continue
        seen.add(key)
        observations.append(observation)
    return observations


def parse_lab_line(line: str) -> dict | None:
    cleaned = line.strip()
    if not cleaned:
        return None
    match = re.search(
        r"(?P<name>[A-Za-zА-Яа-яӨөҮүЁё\-/ ]{2,40})\s+"
        r"(?P<value>-?\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>[A-Za-zА-Яа-яӨөҮү/%^0-9\.]+)?\s*"
        r"(?P<range>\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?)?",
        cleaned,
    )
    if not match:
        return None
    raw_name = match.group("name").strip(" :-")
    test_name = normalize_lab_name(raw_name)
    if len(test_name) < 2:
        return None
    value = match.group("value").replace(",", ".")
    reference_range = normalize_range(match.group("range"))
    status_kind, _ = interpret_lab_status(value, reference_range or "")
    abnormal_flag = None if status_kind == "unknown" else status_kind in {"high", "low"}
    return {
        "test_name": test_name,
        "value": value,
        "unit": match.group("unit"),
        "reference_range": reference_range,
        "abnormal_flag": abnormal_flag,
        "source": "tesseract_ocr",
        "confidence": 62 if reference_range else 52,
    }


def normalize_lab_name(value: str) -> str:
    aliases = {
        "цагаан эс": "WBC",
        "улаан эс": "RBC",
        "гемоглобин": "HGB",
        "ялтас": "PLT",
        "нийт билирубин": "Total bilirubin",
        "билирубин": "Bilirubin",
        "сахар": "Glucose",
    }
    lowered = value.lower()
    for alias, normalized in aliases.items():
        if alias in lowered:
            return normalized
    return value.upper() if re.fullmatch(r"[A-Za-z0-9\-/% ]+", value) else value


def normalize_range(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("–", "-").replace(",", ".").replace(" ", "")


def interpret_lab_status(value: str, reference_range: str) -> tuple[str, str]:
    try:
        numeric_value = float(value)
    except ValueError:
        return "unknown", "Утга тоон хэлбэрээр бүрэн бичигдээгүй тул өндөр/бага эсэхийг ангилах боломжгүй."
    range_parts = reference_range.replace("–", "-").split("-")
    if len(range_parts) != 2:
        return "unknown", "Хэвийн хэмжээ тодорхой бичигдээгүй тул өндөр/бага эсэхийг найдвартай ангилах боломжгүй."
    try:
        low = float(range_parts[0].strip())
        high = float(range_parts[1].strip())
    except ValueError:
        return "unknown", "Хэвийн хэмжээ тоон хэлбэрээр бүрэн бичигдээгүй байна."
    if numeric_value < low:
        return "low", f"Таны бичсэн хэвийн хэмжээ {reference_range}; энэ утга хэвийн хэмжээнээс бага байна."
    if numeric_value > high:
        return "high", f"Таны бичсэн хэвийн хэмжээ {reference_range}; энэ утга хэвийн хэмжээнээс өндөр байна."
    return "normal", f"Таны бичсэн хэвийн хэмжээ {reference_range}; энэ утга хэвийн хэмжээнд багтаж байна."


def plain_language_points(diagnosis: str, lab_name: str, status_kind: str) -> list[str]:
    points = [
        "Нэг шинжилгээ дангаараа бүх оношийг батлахгүй. Зовиур, үзлэг, өмнөх өвчин, хэрэглэж буй эмтэй хамт тайлбарлана.",
        "Өмнөх шинжилгээтэй харьцуулах нь чухал. Өсөж байна уу, буурч байна уу гэдэг нь эмчид илүү их мэдээлэл өгдөг.",
    ]
    if diagnosis:
        points.insert(0, f"{diagnosis} гэдэг нь эмчийн үнэлгээтэй хамт ойлгох нэршил. Шалтгаан, хүндийн зэрэг, цаашдын төлөвлөгөөг эмч тодорхойлно.")
    if lab_name and status_kind == "high":
        points.append(f"{lab_name} өндөр гарсан бол үрэвсэл, эрхтний ачаалал, эмийн нөлөө, эсвэл өвчний явц зэрэг олон боломжит шалтгаантай.")
    elif lab_name and status_kind == "low":
        points.append(f"{lab_name} бага гарсан бол хооллолт, архаг өвчин, цус багадалт, эмийн нөлөө зэрэг шалтгааныг эмч ялгана.")
    elif lab_name and status_kind == "normal":
        points.append(f"{lab_name} хэвийн гарсан ч таны зовиур үргэлжилж байвал бусад шинжилгээ, үзлэг шаардлагатай байж болно.")
    return points


def next_questions(diagnosis: str, lab_name: str, patient_question: str) -> list[str]:
    questions = [
        "Энэ шинжилгээг хэзээ давтан өгөх вэ?",
        "Одоо хэрэглэж буй эм, нэмэлт бүтээгдэхүүн энэ хариунд нөлөөлөх үү?",
        "Ямар шинж илэрвэл яаралтай эмнэлэгт хандах вэ?",
    ]
    if diagnosis:
        questions.insert(0, f"{diagnosis}-ын үед гэртээ юуг ажиглах ёстой вэ?")
    if lab_name:
        questions.insert(0, f"{lab_name} өөрчлөгдсөн гол боломжит шалтгаанууд юу вэ?")
    if patient_question:
        questions.insert(0, f"Таны асуулт: '{patient_question}' гэдгийг дараагийн үзлэг дээр шууд асууж баталгаажуулна.")
    return questions


def safety_notes(diagnosis: str, lab_name: str, status_kind: str) -> list[str]:
    notes = ["Эмээ өөрөө зогсоох, тун өөрчлөхөөс өмнө эмчтэй холбоо барина."]
    text = f"{diagnosis} {lab_name}".lower()
    if status_kind in {"high", "low"}:
        notes.append("Хариу хэвийн бус бол лабораторийн алдаа, түр зуурын өөрчлөлт, бодит өвчний явцын аль нь болохыг эмч ялгана.")
    if "цээж" in text or "тропонин" in text or "зүрх" in text:
        notes.append("Цээжээр хүчтэй өвдөх, амьсгал давчдах, ухаан балартах шинж илэрвэл яаралтай тусламж дуудна.")
    if "alt" in text or "ast" in text or "элэг" in text:
        notes.append("Шарлалт, шээс бараан болох, хүчтэй хэвлийн өвдөлт, бөөлжих шинж илэрвэл эмнэлэгт яаралтай хандана.")
    return notes
