from app.schemas import PatientExplanationCreate
from app.services.image_storage import patient_image_path, read_patient_image, safe_storage_path, store_patient_image
from app.services.patient_ai import parse_lab_line, process_lab_image


PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADElEQVR42mP8z8AARQADeQH9zQAAAABJRU5ErkJggg=="
)


def test_storage_encrypts_file_and_decrypts_on_read():
    stored = store_patient_image(organization_id="org", patient_id="patient", data_url=PNG_DATA_URL)
    encrypted = patient_image_path(stored.object_key).read_bytes()
    decrypted = read_patient_image(stored.object_key)

    assert encrypted != decrypted
    assert decrypted.startswith(b"\x89PNG")
    assert stored.sha256
    assert stored.width == 1
    assert stored.height == 1


def test_storage_blocks_path_traversal():
    try:
        safe_storage_path("../outside")
    except ValueError:
        blocked = True
    else:
        blocked = False

    assert blocked is True


def test_ocr_parser_handles_latin_and_mongolian_lab_names():
    alt = parse_lab_line("ALT 120 U/L 7-40")
    hemoglobin = parse_lab_line("Гемоглобин 10.5 g/dL 12-16")

    assert alt is not None
    assert alt["test_name"] == "ALT"
    assert alt["abnormal_flag"] is True
    assert alt["source"] == "tesseract_ocr"
    assert hemoglobin is not None
    assert hemoglobin["test_name"] == "HGB"


def test_process_lab_image_records_tesseract_metadata_even_with_fallback():
    payload = PatientExplanationCreate(
        lab_name="ALT",
        lab_value="120",
        lab_unit="U/L",
        reference_range="7-40",
        attachment_data_url=PNG_DATA_URL,
    )
    stored = store_patient_image(organization_id="org", patient_id="patient", data_url=PNG_DATA_URL)

    result = process_lab_image(payload, stored)

    assert result.status == "processed"
    assert result.ocr_engine == "tesseract"
    assert result.ocr_languages == "eng+mon"
    assert result.observations[0].test_name == "ALT"
