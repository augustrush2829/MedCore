from sqlalchemy import select

from app.db.models import PatientPortalExplanation

from conftest import get_patient_id, patient_login


PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADElEQVR42mP8z8AARQADeQH9zQAAAABJRU5ErkJggg=="
)


def create_explanation(client, token: str):
    return client.post(
        "/patient-portal/explanations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "diagnosis_text": "Элэгний фермент өссөн",
            "lab_name": "ALT",
            "lab_value": "120",
            "lab_unit": "U/L",
            "reference_range": "7-40",
            "lab_collected_at": "2026-06-01",
            "attachment_name": "lab.png",
            "attachment_content_type": "image/png",
            "attachment_data_url": PNG_DATA_URL,
            "patient_question": "Энэ хариу аюултай юу?",
        },
    )


def test_patient_upload_stores_metadata_without_returning_base64_or_object_key(client, db_session, monkeypatch):
    def fake_generate_json(*args, **kwargs):
        raise RuntimeError("Ollama сервертэй холбогдож чадсангүй")

    monkeypatch.setattr("app.services.patient_ai.generate_json", fake_generate_json)

    token = patient_login(client, "MR-A-001")

    response = create_explanation(client, token)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["patient_id"] == get_patient_id("MR-A-001")
    assert body["attachment_data_url"] is None
    assert body["attachment_object_key"] is None
    assert body["attachment_sha256"]
    assert body["attachment_size_bytes"] > 0
    assert body["has_attachment"] is True
    assert body["extracted_lab_data"]["ocr_engine"] == "local_vision+tesseract"
    assert body["extracted_lab_data"]["ocr_languages"] == "eng+mon"

    stored = db_session.get(PatientPortalExplanation, body["id"])
    assert stored is not None
    assert stored.attachment_object_key
    assert stored.attachment_data_url is None
    assert stored.lab_collected_at.isoformat() == "2026-06-01"


def test_patient_cannot_read_other_patient_explanation_or_image(client):
    token_a = patient_login(client, "MR-A-001")
    token_b = patient_login(client, "MR-B-001")
    created = create_explanation(client, token_a).json()

    list_response = client.get("/patient-portal/explanations", headers={"Authorization": f"Bearer {token_b}"})
    assert list_response.status_code == 200
    assert list_response.json() == []

    detail_response = client.get(
        f"/patient-portal/explanations/{created['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert detail_response.status_code == 404

    image_response = client.get(
        f"/patient-portal/explanations/{created['id']}/image",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert image_response.status_code == 404


def test_patient_can_fetch_own_image_via_presigned_redirect(client):
    token = patient_login(client, "MR-A-001")
    created = create_explanation(client, token).json()

    response = client.get(
        f"/patient-portal/explanations/{created['id']}/image",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://fake-s3.invalid/")
    assert "method=get_object" in location


def test_admin_can_list_portal_uploads_in_own_organization(client):
    patient_token = patient_login(client, "MR-A-001")
    create_explanation(client, patient_token)
    admin_token = client.post("/auth/login", json={"email": "admin@test.mn", "password": "password"}).json()["access_token"]

    response = client.get("/admin/portal-explanations", headers={"Authorization": f"Bearer {admin_token}"})

    assert response.status_code == 200
    assert response.json()[0]["patient_medical_record_no"] == "MR-A-001"


def test_patient_records_are_query_scoped_by_patient_id(db_session, client):
    token = patient_login(client, "MR-A-001")
    created = create_explanation(client, token).json()

    records = db_session.scalars(
        select(PatientPortalExplanation).where(PatientPortalExplanation.patient_id == get_patient_id("MR-A-001"))
    ).all()

    assert [record.id for record in records] == [created["id"]]
