import os
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

TEST_ROOT = Path(__file__).resolve().parent / ".test_state"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DB = TEST_ROOT / "medcore_test.db"
TEST_UPLOADS = TEST_ROOT / "uploads"

sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["PATIENT_UPLOAD_DIR"] = str(TEST_UPLOADS)
os.environ["TESSERACT_LANGUAGES"] = "eng+mon"

from app.core.security import hash_password  # noqa: E402
from app.db.models import Organization, Patient, PatientPortalAccount, User  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app, ensure_mvp_schema  # noqa: E402
from app.routers.auth import login_rate_limiter  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    engine.dispose()
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    TEST_UPLOADS.mkdir(parents=True, exist_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_mvp_schema()
    seed_test_data()
    login_rate_limiter.reset_all()
    yield
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)


@pytest.fixture()
def client():
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()


@pytest.fixture()
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_test_data():
    db = SessionLocal()
    try:
        platform = Organization(name="MedCore Platform", plan="platform", status="active")
        org_a = Organization(name="Hospital A", plan="mvp", status="active")
        org_b = Organization(name="Hospital B", plan="mvp", status="active")
        db.add_all([platform, org_a, org_b])
        db.flush()

        users = [
            User(organization_id=platform.id, email="super@test.mn", name="Super Admin", role="super_admin", password_hash=hash_password("password")),
            User(organization_id=org_a.id, email="admin@test.mn", name="Hospital Admin", role="admin", password_hash=hash_password("password")),
            User(organization_id=org_a.id, email="doctor@test.mn", name="Doctor A", role="doctor", password_hash=hash_password("password")),
            User(organization_id=org_a.id, email="auditor@test.mn", name="Auditor A", role="auditor", password_hash=hash_password("password")),
            User(organization_id=org_b.id, email="doctor-b@test.mn", name="Doctor B", role="doctor", password_hash=hash_password("password")),
        ]
        db.add_all(users)
        db.flush()

        patient_a = Patient(
            organization_id=org_a.id,
            medical_record_no="MR-A-001",
            name="Patient A",
            date_of_birth=date(1980, 1, 1),
            age=46,
            gender="female",
        )
        patient_b = Patient(
            organization_id=org_b.id,
            medical_record_no="MR-B-001",
            name="Patient B",
            date_of_birth=date(1970, 1, 1),
            age=56,
            gender="male",
        )
        db.add_all([patient_a, patient_b])
        db.flush()

        db.add_all(
            [
                PatientPortalAccount(
                    organization_id=org_a.id,
                    patient_id=patient_a.id,
                    login_identifier="MR-A-001",
                    password_hash=hash_password("patientpass"),
                ),
                PatientPortalAccount(
                    organization_id=org_b.id,
                    patient_id=patient_b.id,
                    login_identifier="MR-B-001",
                    password_hash=hash_password("patientpass"),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


def login(client: TestClient, email: str, password: str = "password") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def patient_login(client: TestClient, login_identifier: str, password: str = "patientpass") -> str:
    response = client.post("/patient-portal/login", json={"login_identifier": login_identifier, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def get_patient_id(medical_record_no: str) -> str:
    db = SessionLocal()
    try:
        patient = db.scalar(select(Patient).where(Patient.medical_record_no == medical_record_no))
        assert patient is not None
        return patient.id
    finally:
        db.close()
