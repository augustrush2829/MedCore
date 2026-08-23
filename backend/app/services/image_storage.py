import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet

from app.core.config import get_settings


@dataclass(frozen=True)
class StoredImage:
    object_key: str
    content_type: str
    sha256: str
    size_bytes: int
    width: int | None
    height: int | None


@dataclass(frozen=True)
class StoredFile:
    object_key: str
    content_type: str
    sha256: str
    size_bytes: int
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class ImagePayload:
    content_type: str
    data: bytes


def store_patient_image(*, organization_id: str, patient_id: str, data_url: str) -> StoredImage:
    image = parse_image_data_url(data_url)
    stored = store_patient_file_payload(organization_id=organization_id, patient_id=patient_id, payload=image)
    return StoredImage(
        object_key=stored.object_key,
        content_type=stored.content_type,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        width=stored.width,
        height=stored.height,
    )


def store_patient_file(*, organization_id: str, patient_id: str, data_url: str) -> StoredFile:
    return store_patient_file_payload(
        organization_id=organization_id,
        patient_id=patient_id,
        payload=parse_file_data_url(data_url),
    )


def store_patient_file_payload(*, organization_id: str, patient_id: str, payload: ImagePayload) -> StoredFile:
    sha256 = hashlib.sha256(payload.data).hexdigest()
    width, height = detect_image_dimensions(payload.content_type, payload.data)
    extension = extension_for_content_type(payload.content_type)
    object_key = f"{organization_id}/{patient_id}/{uuid4()}{extension}"
    path = storage_root() / object_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encrypt_bytes(payload.data))
    return StoredFile(
        object_key=object_key,
        content_type=payload.content_type,
        sha256=sha256,
        size_bytes=len(payload.data),
        width=width,
        height=height,
    )


def read_patient_image(object_key: str) -> bytes:
    path = safe_storage_path(object_key)
    return decrypt_bytes(path.read_bytes())


def patient_image_path(object_key: str) -> Path:
    return safe_storage_path(object_key)


def storage_root() -> Path:
    configured = Path(get_settings().patient_upload_dir)
    if configured.is_absolute():
        return configured.resolve()
    backend_root = Path(__file__).resolve().parents[2]
    return (backend_root / configured).resolve()


def encryption_key() -> bytes:
    digest = hashlib.sha256(get_settings().jwt_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_bytes(data: bytes) -> bytes:
    return Fernet(encryption_key()).encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    return Fernet(encryption_key()).decrypt(data)


def safe_storage_path(object_key: str) -> Path:
    root = storage_root()
    path = (root / object_key).resolve()
    if root not in path.parents and path != root:
        raise ValueError("Invalid object key")
    return path


def parse_image_data_url(data_url: str) -> ImagePayload:
    payload = parse_file_data_url(data_url)
    if not payload.content_type.startswith("image/"):
        raise ValueError("Зургийн data URL буруу байна.")
    return payload


def parse_file_data_url(data_url: str) -> ImagePayload:
    header, separator, encoded = data_url.partition(",")
    if not separator or not header.startswith("data:") or ";base64" not in header:
        raise ValueError("Файлын data URL буруу байна.")
    content_type = header.removeprefix("data:").split(";", 1)[0]
    if content_type not in {"image/png", "image/jpeg", "image/jpg", "image/webp", "application/pdf", "text/plain"}:
        raise ValueError("Дэмжигдээгүй file content type байна.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError("Файлын base64 payload уншигдсангүй.") from exc
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("Файл 10MB-аас их байна.")
    return ImagePayload(content_type=content_type, data=data)


def extension_for_content_type(content_type: str) -> str:
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
        "text/plain": ".txt",
    }.get(content_type, ".img")


def detect_image_dimensions(content_type: str, data: bytes) -> tuple[int | None, int | None]:
    if content_type == "image/png" and len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if content_type in {"image/jpeg", "image/jpg"}:
        return detect_jpeg_dimensions(data)
    return None, None


def detect_jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None, None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        segment_length = int.from_bytes(data[index:index + 2], "big")
        if marker in range(0xC0, 0xC4):
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            return width, height
        index += segment_length
    return None, None
