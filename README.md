# MedCore

MedCore is an AI-assisted clinical decision support MVP for doctors. The current repo contains:

- Next.js frontend under `src/`
- FastAPI backend under `backend/`
- PostgreSQL dev service in `docker-compose.yml`

The backend follows `MedCore_Architecture_Report.docx`: RBAC, tenant-scoped patient/case data, structured clinical input, AI response orchestration, doctor confirmation, feedback capture, and append-only audit logs.

## Frontend

```bash
npm install
npm run dev
```

Frontend dev server: `http://localhost:3000`

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Backend docs: `http://localhost:8000/docs`

Demo login:

```text
batbold@clinic.mn / password
```

## PostgreSQL

```bash
docker compose up -d postgres
```

Default `.env.example` points to PostgreSQL. Without `.env`, the backend uses local SQLite for quick development.


  users:
  batbold@clinic.mn doctor
  auditor@clinic.mn auditor
  admin@clinic.mn admin
  super@medcore.mn super_admin   change-me-local
   Нэвтрэх нэр: MR-PATIENT-TEST
  Нууц үг: Patient@12345

