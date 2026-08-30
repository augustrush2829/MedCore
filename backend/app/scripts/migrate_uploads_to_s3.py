"""One-time migration: copy existing local patient-upload files into the
S3-compatible object store, verifying each copy with a checksum comparison.

Deliberately self-contained and separate from app.services.image_storage -
that module is free to change (it will, once the app itself is cut over to
S3) without breaking this script's ability to read the *old* local/Fernet
format on a machine that still has those files sitting on disk.

Never deletes or modifies the local originals. Safe to re-run: an object
that's already in S3 with matching content is left alone.

Usage (from backend/, with the venv active and the same .env the app uses):
    python -m app.scripts.migrate_uploads_to_s3 [--dry-run] [--report-dir PATH]

--dry-run reads and checksums local files and reports what would happen,
without uploading anything to S3.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from botocore.exceptions import ClientError
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.s3_client import get_s3_client
from app.db.models import CaseAttachment, PatientPortalExplanation
from app.db.session import SessionLocal


@dataclass
class FileResult:
    source_table: str
    record_id: str
    object_key: str
    outcome: str  # migrated | already_migrated | skipped_no_key | failed
    detail: str = ""


def local_encryption_key() -> bytes:
    digest = hashlib.sha256(get_settings().jwt_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def local_storage_root() -> Path:
    configured = Path(get_settings().patient_upload_dir)
    if configured.is_absolute():
        return configured.resolve()
    backend_root = Path(__file__).resolve().parents[3]
    return (backend_root / configured).resolve()


def read_and_decrypt_local_file(object_key: str) -> bytes:
    root = local_storage_root()
    path = (root / object_key).resolve()
    if root not in path.parents and path != root:
        raise ValueError(f"Object key escapes storage root: {object_key!r}")
    encrypted = path.read_bytes()
    return Fernet(local_encryption_key()).decrypt(encrypted)


def object_exists_in_s3(*, bucket: str, key: str) -> bool:
    try:
        get_s3_client().head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def migrate_one(
    *,
    source_table: str,
    record_id: str,
    object_key: str | None,
    content_type: str | None,
    recorded_sha256: str | None,
    dry_run: bool,
) -> FileResult:
    if not object_key:
        return FileResult(source_table, record_id, "", "skipped_no_key")

    settings = get_settings()
    local_path = local_storage_root() / object_key
    if not local_path.exists():
        return FileResult(source_table, record_id, object_key, "failed", "local file missing")

    try:
        plaintext = read_and_decrypt_local_file(object_key)
    except Exception as exc:  # noqa: BLE001 - report every failure mode, don't crash the batch
        return FileResult(source_table, record_id, object_key, "failed", f"decrypt failed: {exc}")

    local_sha256 = hashlib.sha256(plaintext).hexdigest()
    if recorded_sha256 and local_sha256 != recorded_sha256:
        return FileResult(
            source_table, record_id, object_key, "failed",
            f"local file checksum {local_sha256} does not match DB record {recorded_sha256}",
        )

    if object_exists_in_s3(bucket=settings.s3_bucket, key=object_key):
        try:
            remote = get_s3_client().get_object(Bucket=settings.s3_bucket, Key=object_key)
            remote_sha256 = hashlib.sha256(remote["Body"].read()).hexdigest()
        except Exception as exc:  # noqa: BLE001
            return FileResult(source_table, record_id, object_key, "failed", f"could not re-verify existing S3 object: {exc}")
        if remote_sha256 == local_sha256:
            return FileResult(source_table, record_id, object_key, "already_migrated", "checksum verified")
        return FileResult(
            source_table, record_id, object_key, "failed",
            f"object already exists in S3 but checksum {remote_sha256} != local {local_sha256}",
        )

    if dry_run:
        return FileResult(source_table, record_id, object_key, "migrated", "dry-run: would upload, checksum verified locally")

    try:
        get_s3_client().put_object(
            Bucket=settings.s3_bucket,
            Key=object_key,
            Body=plaintext,
            ContentType=content_type or "application/octet-stream",
        )
        remote = get_s3_client().get_object(Bucket=settings.s3_bucket, Key=object_key)
        remote_sha256 = hashlib.sha256(remote["Body"].read()).hexdigest()
    except Exception as exc:  # noqa: BLE001
        return FileResult(source_table, record_id, object_key, "failed", f"upload/verify failed: {exc}")

    if remote_sha256 != local_sha256:
        return FileResult(
            source_table, record_id, object_key, "failed",
            f"uploaded object checksum {remote_sha256} != local {local_sha256}",
        )
    return FileResult(source_table, record_id, object_key, "migrated", "checksum verified")


def run(*, dry_run: bool) -> list[FileResult]:
    results: list[FileResult] = []
    db = SessionLocal()
    try:
        explanations = db.query(PatientPortalExplanation).filter(
            PatientPortalExplanation.attachment_object_key.isnot(None)
        ).all()
        for explanation in explanations:
            results.append(
                migrate_one(
                    source_table="patient_portal_explanations",
                    record_id=explanation.id,
                    object_key=explanation.attachment_object_key,
                    content_type=explanation.attachment_content_type,
                    recorded_sha256=explanation.attachment_sha256,
                    dry_run=dry_run,
                )
            )

        attachments = db.query(CaseAttachment).all()
        for attachment in attachments:
            results.append(
                migrate_one(
                    source_table="case_attachments",
                    record_id=attachment.id,
                    object_key=attachment.object_key,
                    content_type=attachment.content_type,
                    recorded_sha256=attachment.sha256,
                    dry_run=dry_run,
                )
            )
    finally:
        db.close()
    return results


def write_report(results: list[FileResult], report_dir: Path, *, dry_run: bool) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"s3_migration_report_{timestamp}.json"
    by_outcome: dict[str, int] = {}
    for result in results:
        by_outcome[result.outcome] = by_outcome.get(result.outcome, 0) + 1
    report = {
        "generated_at": timestamp,
        "dry_run": dry_run,
        "total_records": len(results),
        "by_outcome": by_outcome,
        "failures": [asdict(r) for r in results if r.outcome == "failed"],
        "results": [asdict(r) for r in results],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_path


def print_summary(results: list[FileResult], *, dry_run: bool, report_path: Path) -> None:
    by_outcome: dict[str, int] = {}
    for result in results:
        by_outcome[result.outcome] = by_outcome.get(result.outcome, 0) + 1
    print(f"{'DRY RUN — ' if dry_run else ''}S3 upload migration finished. {len(results)} record(s) considered.")
    for outcome, count in sorted(by_outcome.items()):
        print(f"  {outcome}: {count}")
    failures = [r for r in results if r.outcome == "failed"]
    if failures:
        print("\nFAILURES (local originals untouched, safe to investigate and re-run):")
        for result in failures:
            print(f"  [{result.source_table}] {result.record_id} ({result.object_key}): {result.detail}")
    print(f"\nFull report written to {report_path}")
    print("Local files under storage/patient_uploads were not modified or deleted by this script.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report what would happen without uploading to S3")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "migration_reports",
        help="Directory to write the JSON migration report into",
    )
    args = parser.parse_args()

    results = run(dry_run=args.dry_run)
    report_path = write_report(results, args.report_dir, dry_run=args.dry_run)
    print_summary(results, dry_run=args.dry_run, report_path=report_path)


if __name__ == "__main__":
    main()
