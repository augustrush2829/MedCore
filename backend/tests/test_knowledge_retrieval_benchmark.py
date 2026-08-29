"""Baseline benchmark for retrieve_context() against the real knowledge base.

This exercises the sqlite/Python full-table-scan path (_retrieve_context_python_scan
in app/services/knowledge.py) - the only path this test suite can run, since CI/local
dev use sqlite and pgvector's HNSW index (see the 2af1460cd260 Alembic migration and
_retrieve_context_pgvector) only exists on Postgres.

Measured on this machine against the full data/mn_edoctor_kb dataset (219 source
records -> 570 knowledge_chunks rows, the entire current knowledge base):
  - single retrieve_context() call: ~51 ms
  - 50 sequential calls: ~2.5 s total (50.7 ms/call average)

That's the "before" number. It's fast today only because the table is tiny and this
runs single-instance with no concurrent load. The Postgres/HNSW "after" number needs
to be captured separately against a real pgvector instance (e.g. via `docker compose
up postgres`, run ingest_knowledge.py, then time retrieve_context() through a
postgresql:// DATABASE_URL) - that benchmark isn't runnable in this sandbox, which has
no Postgres/Docker available. What this test protects going forward is a regression
that turns the linear scan quadratic or worse as chunk count grows.
"""

import time
from pathlib import Path

from app.services.knowledge import ingest_knowledge_path, retrieve_context

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_PATH = REPO_ROOT / "data" / "mn_edoctor_kb"


def test_retrieve_context_benchmark_full_knowledge_base(db_session):
    assert KB_PATH.exists(), f"expected knowledge base at {KB_PATH}"

    result = ingest_knowledge_path(db_session, KB_PATH, category="clinical", version="benchmark")
    assert result["chunks"] > 0

    query = "цусны даралт өндөр, толгой өвдөх"

    start = time.perf_counter()
    for _ in range(50):
        retrieve_context(db_session, query, top_k=6)
    elapsed = time.perf_counter() - start

    average_ms = (elapsed / 50) * 1000
    # Generous regression guard, not a performance target: catches an
    # accidental N^2 blowup (e.g. re-embedding the query per chunk), not
    # minor timing noise.
    assert average_ms < 500, f"retrieve_context() averaged {average_ms:.2f}ms/call over {result['chunks']} chunks"
