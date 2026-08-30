from app.core import s3_client
from s3_fake import FakeS3Client


def test_generate_presigned_get_url_targets_configured_bucket_and_key(monkeypatch):
    fake = FakeS3Client()
    monkeypatch.setattr(s3_client, "get_s3_client", lambda: fake)

    url = s3_client.generate_presigned_get_url("org/patient/file.png", filename="lab.png", content_type="image/png")

    settings = s3_client.get_settings()
    assert f"/{settings.s3_bucket}/org/patient/file.png" in url
    assert f"expires={settings.s3_presigned_url_expire_seconds}" in url


def test_generate_presigned_get_url_respects_explicit_expiry(monkeypatch):
    fake = FakeS3Client()
    monkeypatch.setattr(s3_client, "get_s3_client", lambda: fake)

    url = s3_client.generate_presigned_get_url("org/patient/file.png", expires_in=30)

    assert "expires=30" in url
