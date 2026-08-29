"""Baseline benchmark for retrieve_context() against the real knowledge base.

This exercises the sqlite/Python full-table-scan path (_retrieve_context_python_scan
in app/services/knowledge.py) - the only path this test suite can run, since CI/local
dev use sqlite and pgvector's HNSW index (see the 2af1460cd260 Alembic migration and
_retrieve_context_pgvector) only exists on Postgres.

Measured on this machine against the full data/mn_edoctor_kb dataset (219 source
records -> 570 knowledge_chunks rows, the entire current knowledge base):
  - single retrieve_context() call: ~51 ms (fake/mocked embedding, as used here)
  - 50 sequential calls: ~2.5 s total (50.7 ms/call average)

That sqlite number is the "before" path with a mocked embedding function (this test
suite's autouse fixture replaces embed_text() - see conftest.py - so no real model
inference happens here). What this test actually protects going forward is a
regression that turns the linear scan quadratic or worse as chunk count grows.

The real "before vs after" comparison was captured separately against real Postgres
16.15 + pgvector 0.8.6 (native Windows build; no Docker was available on that
machine), same 570-chunk dataset, real intfloat/multilingual-e5-base embeddings for
both sides, isolating pure retrieval-mechanism cost from embedding cost:
  - BEFORE (old Python full-table cosine scan, run against Postgres data): ~156.5 ms/call
  - AFTER  (_retrieve_context_pgvector, letting Postgres pick its own plan):  ~2.5 ms/call
  - ~62x faster

Important caveat found via EXPLAIN ANALYZE: at this table size (570 rows), Postgres's
query planner does NOT use the ix_knowledge_chunks_embedding_hnsw index - it picks a
Seq Scan + in-memory sort, because the planner's cost model judges that cheaper than
an HNSW index scan at such a small row count. Forcing `SET enable_seqscan = off`
confirms the index itself is valid and does get picked (Index Scan using
ix_knowledge_chunks_embedding_hnsw) with a comparable execution time (~0.9ms vs
~1.3ms for the seq scan) - so the index isn't broken, it's just not yet worth using
at this scale. The ~62x win measured above therefore comes mainly from moving the
distance computation and sort into Postgres/C instead of pulling all 570 embeddings
into the Python process, not from the HNSW index specifically. The index is groundwork
for when the knowledge base is large enough (expect low thousands of rows or more,
depending on data) that Postgres's planner starts choosing it automatically - no code
or config change needed when that happens, and this can be re-verified any time with
`EXPLAIN ANALYZE` on the query in _retrieve_context_pgvector().
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
