import hashlib
import json
import math
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import KnowledgeChunk, KnowledgeDocument
from app.services.gemini import embed_text, lexical_embedding


SUPPORTED_SUFFIXES = {".md": "text/markdown", ".txt": "text/plain", ".json": "application/json", ".pdf": "application/pdf"}


def ingest_knowledge_path(db: Session, path: Path, *, category: str = "clinical", version: str = "local") -> dict:
    files = [path] if path.is_file() else [item for item in path.rglob("*") if item.suffix.lower() in SUPPORTED_SUFFIXES]
    summary = {"documents": 0, "chunks": 0, "skipped": 0}
    for file_path in sorted(files):
        result = ingest_knowledge_file(db, file_path, category=category, version=version)
        summary["documents"] += int(result["document_created"])
        summary["chunks"] += result["chunks"]
        summary["skipped"] += int(result["skipped"])
    db.commit()
    return summary


def ingest_knowledge_file(db: Session, path: Path, *, category: str, version: str) -> dict:
    raw = path.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    existing = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.source_hash == source_hash))
    if existing:
        return {"document_created": False, "chunks": 0, "skipped": True}

    text = extract_text(path, raw)
    if not text.strip():
        return {"document_created": False, "chunks": 0, "skipped": True}

    stale = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.source_path == str(path)))
    if stale:
        db.delete(stale)
        db.flush()

    document = KnowledgeDocument(
        title=path.stem.replace("_", " "),
        source_path=str(path),
        source_hash=source_hash,
        content_type=SUPPORTED_SUFFIXES[path.suffix.lower()],
        category=category,
        version=version,
        metadata_json={"bytes": len(raw)},
    )
    db.add(document)
    db.flush()

    chunks = chunk_text(text)
    for index, chunk in enumerate(chunks):
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                embedding=embed_text(chunk),
                embedding_model=get_settings().gemini_embedding_model if get_settings().gemini_api_key else "lexical-fallback",
                category=category,
                source_title=document.title,
                source_path=document.source_path,
                metadata_json={"source_hash": source_hash},
            )
        )
    return {"document_created": True, "chunks": len(chunks), "skipped": False}


def retrieve_context(db: Session, query: str, *, top_k: int | None = None) -> list[KnowledgeChunk]:
    query_vector = embed_text(query) if get_settings().gemini_api_key else lexical_embedding(query)
    chunks = list(db.scalars(select(KnowledgeChunk)).all())
    scored = [(cosine(query_vector, chunk.embedding or []), chunk) for chunk in chunks]
    scored.sort(key=lambda item: item[0], reverse=True)
    limit = top_k or get_settings().rag_top_k
    return [chunk for score, chunk in scored[:limit] if score > 0]


def extract_text(path: Path, raw: bytes) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return raw.decode("utf-8", errors="replace")
    if suffix == ".json":
        data = json.loads(raw.decode("utf-8"))
        return json.dumps(data, ensure_ascii=False, indent=2)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""


def chunk_text(text: str, *, max_chars: int = 1600, overlap: int = 200) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(normalized) <= max_chars:
        return [normalized] if normalized else []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + max_chars)
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    dot = sum(left[i] * right[i] for i in range(size))
    left_mag = math.sqrt(sum(value * value for value in left[:size]))
    right_mag = math.sqrt(sum(value * value for value in right[:size]))
    if not left_mag or not right_mag:
        return 0.0
    return dot / (left_mag * right_mag)
