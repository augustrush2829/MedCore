from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db import models
from app.db.session import Base, engine
from app.routers import admin, audit, auth, cases, dashboard, health, patient_portal, patients


settings = get_settings()

app = FastAPI(
    title="MedCore API",
    version="0.1.0",
    description="Clinical decision support MVP backend with RBAC, tenant isolation, AI response audit, and doctor confirmation workflow.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables_for_mvp() -> None:
    # Alembic should own production migrations. Auto-create keeps the MVP runnable.
    ensure_postgres_extensions()
    Base.metadata.create_all(bind=engine)
    ensure_mvp_schema()


def ensure_postgres_extensions() -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def ensure_mvp_schema() -> None:
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "patient_portal_explanations" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("patient_portal_explanations")}
    required_columns = {
        "attachment_object_key": "VARCHAR(500)",
        "attachment_sha256": "VARCHAR(64)",
        "attachment_size_bytes": "INTEGER",
        "attachment_width": "INTEGER",
        "attachment_height": "INTEGER",
        "extracted_lab_data": "JSON NOT NULL DEFAULT '{}'",
        "extraction_status": "VARCHAR(50) NOT NULL DEFAULT 'not_requested'",
        "extraction_model": "VARCHAR(100)",
    }
    with engine.begin() as connection:
        for column_name, definition in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE patient_portal_explanations ADD COLUMN {column_name} {definition}"))


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(patients.router)
app.include_router(cases.router)
app.include_router(audit.router)
app.include_router(patient_portal.router)
app.include_router(admin.router)

__all__ = ["app", "models"]
