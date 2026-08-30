import hashlib
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from app.scripts import migrate_uploads_to_s3 as migrate
from s3_fake import FakeS3Client


@pytest.fixture()
def env(tmp_path, monkeypatch):
    settings = SimpleNamespace(jwt_secret="test-jwt-secret", patient_upload_dir=str(tmp_path), s3_bucket="test-bucket")
    monkeypatch.setattr(migrate, "get_settings", lambda: settings)
    fake_client = FakeS3Client()
    monkeypatch.setattr(migrate, "get_s3_client", lambda: fake_client)
    return tmp_path, settings, fake_client


def write_local_encrypted_file(tmp_path, object_key: str, plaintext: bytes) -> None:
    key = migrate.local_encryption_key()
    path = tmp_path / object_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(Fernet(key).encrypt(plaintext))


def test_migrate_one_uploads_and_verifies_checksum(env):
    tmp_path, settings, fake_client = env
    plaintext = b"fake-lab-image-bytes"
    write_local_encrypted_file(tmp_path, "org/patient/file.png", plaintext)
    sha256 = hashlib.sha256(plaintext).hexdigest()

    result = migrate.migrate_one(
        source_table="patient_portal_explanations",
        record_id="rec-1",
        object_key="org/patient/file.png",
        content_type="image/png",
        recorded_sha256=sha256,
        dry_run=False,
    )

    assert result.outcome == "migrated"
    stored = fake_client.objects[(settings.s3_bucket, "org/patient/file.png")]
    assert stored["Body"] == plaintext
    assert stored["ContentType"] == "image/png"


def test_migrate_one_dry_run_does_not_upload(env):
    tmp_path, settings, fake_client = env
    plaintext = b"fake-lab-image-bytes"
    write_local_encrypted_file(tmp_path, "org/patient/file.png", plaintext)
    sha256 = hashlib.sha256(plaintext).hexdigest()

    result = migrate.migrate_one(
        source_table="patient_portal_explanations",
        record_id="rec-1",
        object_key="org/patient/file.png",
        content_type="image/png",
        recorded_sha256=sha256,
        dry_run=True,
    )

    assert result.outcome == "migrated"
    assert "dry-run" in result.detail
    assert fake_client.objects == {}


def test_migrate_one_flags_checksum_mismatch_against_db_record(env):
    tmp_path, _settings, _fake_client = env
    write_local_encrypted_file(tmp_path, "org/patient/file.png", b"actual-bytes")

    result = migrate.migrate_one(
        source_table="patient_portal_explanations",
        record_id="rec-1",
        object_key="org/patient/file.png",
        content_type="image/png",
        recorded_sha256="0" * 64,
        dry_run=False,
    )

    assert result.outcome == "failed"
    assert "does not match" in result.detail


def test_migrate_one_reports_missing_local_file(env):
    result = migrate.migrate_one(
        source_table="case_attachments",
        record_id="rec-2",
        object_key="org/patient/missing.png",
        content_type="image/png",
        recorded_sha256=None,
        dry_run=False,
    )

    assert result.outcome == "failed"
    assert "missing" in result.detail


def test_migrate_one_skips_records_without_object_key(env):
    result = migrate.migrate_one(
        source_table="patient_portal_explanations",
        record_id="rec-3",
        object_key=None,
        content_type=None,
        recorded_sha256=None,
        dry_run=False,
    )

    assert result.outcome == "skipped_no_key"


def test_migrate_one_is_idempotent_when_already_uploaded_with_matching_checksum(env):
    tmp_path, settings, fake_client = env
    plaintext = b"fake-lab-image-bytes"
    write_local_encrypted_file(tmp_path, "org/patient/file.png", plaintext)
    sha256 = hashlib.sha256(plaintext).hexdigest()
    fake_client.put_object(Bucket=settings.s3_bucket, Key="org/patient/file.png", Body=plaintext, ContentType="image/png")

    result = migrate.migrate_one(
        source_table="patient_portal_explanations",
        record_id="rec-1",
        object_key="org/patient/file.png",
        content_type="image/png",
        recorded_sha256=sha256,
        dry_run=False,
    )

    assert result.outcome == "already_migrated"


def test_migrate_one_flags_existing_s3_object_with_wrong_content(env):
    tmp_path, settings, fake_client = env
    plaintext = b"fake-lab-image-bytes"
    write_local_encrypted_file(tmp_path, "org/patient/file.png", plaintext)
    sha256 = hashlib.sha256(plaintext).hexdigest()
    fake_client.put_object(Bucket=settings.s3_bucket, Key="org/patient/file.png", Body=b"some-other-bytes", ContentType="image/png")

    result = migrate.migrate_one(
        source_table="patient_portal_explanations",
        record_id="rec-1",
        object_key="org/patient/file.png",
        content_type="image/png",
        recorded_sha256=sha256,
        dry_run=False,
    )

    assert result.outcome == "failed"
    assert "already exists" in result.detail
