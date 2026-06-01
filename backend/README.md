# MedCore Backend

FastAPI MVP backend aligned with `MedCore_Architecture_Report.docx`.

## Includes

- Auth demo endpoint with JWT and RBAC context
- Organization scoped patient and clinical case APIs
- Structured symptoms, labs, medications, supplements, allergies
- Rule-based AI MVP for differential diagnosis, lab interpretation, medication warnings, causality, citations
- Doctor decision and feedback capture
- Append-only audit log APIs
- PostgreSQL-ready SQLAlchemy schema

## Run

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Start PostgreSQL from the repo root:

```bash
docker compose up -d postgres
```

Seed demo data:

```bash
python -m app.seed
```

Demo login:

```json
{
  "email": "batbold@clinic.mn",
  "password": "password"
}
```

API docs: `http://localhost:8000/docs`

