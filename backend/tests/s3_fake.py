"""In-memory fake of the subset of the boto3 S3 client this app uses.

Shared across test files so upload-path, migration-script, and presigned-URL
tests don't each hand-roll their own stub. Not a general boto3 mock - only
implements the calls app.core.s3_client / app.services.image_storage make.
"""

from __future__ import annotations

import io

from botocore.exceptions import ClientError


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str | None = None, **_kwargs) -> dict:
        self.objects[(Bucket, Key)] = {"Body": bytes(Body), "ContentType": ContentType}
        return {}

    def get_object(self, *, Bucket: str, Key: str, **_kwargs) -> dict:
        try:
            stored = self.objects[(Bucket, Key)]
        except KeyError:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject") from None
        return {"Body": io.BytesIO(stored["Body"]), "ContentType": stored.get("ContentType")}

    def head_object(self, *, Bucket: str, Key: str, **_kwargs) -> dict:
        if (Bucket, Key) not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        return {}

    def head_bucket(self, *, Bucket: str, **_kwargs) -> dict:
        return {}

    def create_bucket(self, *, Bucket: str, **_kwargs) -> dict:
        return {}

    def generate_presigned_url(self, ClientMethod: str, Params: dict, ExpiresIn: int) -> str:
        return f"https://fake-s3.invalid/{Params['Bucket']}/{Params['Key']}?method={ClientMethod}&expires={ExpiresIn}"
