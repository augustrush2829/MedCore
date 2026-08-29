"""add hnsw index on knowledge_chunks embedding

Revision ID: 2af1460cd260
Revises:
Create Date: 2026-08-30 03:12:57.783021

Adds a pgvector HNSW index on knowledge_chunks.embedding so nearest-neighbor
retrieval runs as a real index scan in Postgres instead of the app pulling
every chunk into a backend process and scoring cosine similarity in Python
(see retrieve_context() in app/services/knowledge.py).

HNSW (rather than ivfflat) because it needs no `lists` tuning tied to
current row count - the knowledge base is small today (~200 source records)
but is expected to grow, and ivfflat's recommended `lists` value depends on
table size at index-build time. Requires pgvector >= 0.5.0 (the
pgvector/pgvector:pg16 docker-compose image satisfies this).

This is the first Alembic migration in this project. Table creation itself
is still handled by Base.metadata.create_all() at app startup (see
app/main.py) - Alembic is being introduced here to own schema changes,
like this index, that create_all doesn't express well. A database that
predates this migration needs `alembic stamp head` run once schema drift
has been reconciled, since there is no earlier baseline revision to
autogenerate against.

Verified against real Postgres 16.15 + pgvector 0.8.6: the index builds and
is valid (`SET enable_seqscan = off` forces an Index Scan using this index
with correct results), but at the knowledge base's current size (570 rows)
Postgres's planner prefers a Seq Scan by default - the cost model judges
that cheaper than an HNSW scan at such a small row count, and their actual
execution times are in fact close (~0.9ms index scan vs ~1.3ms seq scan).
This is expected pgvector/Postgres behavior, not a broken index: the
planner will switch to using it automatically once the table is large
enough to make it worthwhile, with no migration or config change needed.
See backend/tests/test_knowledge_retrieval_benchmark.py for the full
before/after numbers.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2af1460cd260'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_knowledge_chunks_embedding_hnsw"
TABLE_NAME = "knowledge_chunks"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # HNSW indexes are a pgvector/Postgres feature. Non-Postgres
        # environments (sqlite, used for local dev and tests) keep using the
        # in-process Python cosine scan in retrieve_context().
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            f"""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME}
            ON {TABLE_NAME}
            USING hnsw (embedding vector_cosine_ops)
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}")
