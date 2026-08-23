from datetime import date
import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import (
    ClinicalCase,
    Encounter,
    Allergy,
    LabResult,
    Medication,
    MedicationIngredient,
    Organization,
    Patient,
    PatientPortalAccount,
    Supplement,
    Symptom,
    User,
)
from app.db.session import Base, SessionLocal, engine


def seed() -> None:
    if os.getenv("MEDCORE_DEMO_DATA") != "true":
        print("Seed skipped. Set MEDCORE_DEMO_DATA=true only for local demo data.")
        return
    staff_password = os.getenv("DEMO_STAFF_PASSWORD")
    patient_password = os.getenv("DEMO_PATIENT_PASSWORD")
    if not staff_password or not patient_password:
        print("Seed skipped. Set DEMO_STAFF_PASSWORD and DEMO_PATIENT_PASSWORD for local demo data.")
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_doctor = db.scalar(select(User).where(User.email == "batbold@clinic.mn"))
        if existing_doctor:
            platform_org = db.scalar(select(Organization).where(Organization.name == "MedCore Platform"))
            if not platform_org:
                platform_org = Organization(name="MedCore Platform", plan="platform", status="active")
                db.add(platform_org)
                db.flush()
            if not db.scalar(select(User).where(User.email == "super@medcore.mn")):
                db.add(
                    User(
                        organization_id=platform_org.id,
                        email="super@medcore.mn",
                        name="MedCore Super Admin",
                        role="super_admin",
                        password_hash=hash_password(staff_password),
                    )
                )
            if not db.scalar(select(User).where(User.email == "admin@clinic.mn")):
                db.add(
                    User(
                        organization_id=existing_doctor.organization_id,
                        email="admin@clinic.mn",
                        name="Байгууллагын админ",
                        role="admin",
                        password_hash=hash_password(staff_password),
                    )
                )
            patient = db.scalar(select(Patient).where(Patient.medical_record_no == "MR-2024-001"))
            if patient and not db.scalar(select(PatientPortalAccount).where(PatientPortalAccount.patient_id == patient.id)):
                db.add(
                    PatientPortalAccount(
                        organization_id=patient.organization_id,
                        patient_id=patient.id,
                        login_identifier="MR-2024-001",
                        password_hash=hash_password(patient_password),
                    )
                )
                db.commit()
                print("Seed account updates created.")
                return
            db.commit()
            print("Seed data already exists.")
            return

        platform_org = Organization(name="MedCore Platform", plan="platform", status="active")
        org = Organization(name="Улаанбаатар Эмнэлэг №1")
        db.add_all([platform_org, org])
        db.flush()

        super_admin = User(
            organization_id=platform_org.id,
            email="super@medcore.mn",
            name="MedCore Super Admin",
            role="super_admin",
            password_hash=hash_password(staff_password),
        )
        doctor = User(
            organization_id=org.id,
            email="batbold@clinic.mn",
            name="Д. Батболд",
            role="doctor",
            password_hash=hash_password(staff_password),
        )
        auditor = User(
            organization_id=org.id,
            email="auditor@clinic.mn",
            name="Чанарын хянагч",
            role="auditor",
            password_hash=hash_password(staff_password),
        )
        admin = User(
            organization_id=org.id,
            email="admin@clinic.mn",
            name="Байгууллагын админ",
            role="admin",
            password_hash=hash_password(staff_password),
        )
        db.add_all([super_admin, doctor, auditor, admin])
        db.flush()

        patient = Patient(
            organization_id=org.id,
            name="Б. Энхжаргал",
            age=45,
            gender="female",
            medical_record_no="MR-2024-001",
            date_of_birth=date(1979, 3, 15),
            phone="+976 9911-2233",
            last_visit=date(2026, 5, 20),
        )
        db.add(patient)
        db.flush()
        db.add(Allergy(organization_id=org.id, patient_id=patient.id, substance="Aspirin", reaction="Тууралт", severity="moderate", verified_status="doctor_verified"))
        db.add(
            PatientPortalAccount(
                organization_id=org.id,
                patient_id=patient.id,
                login_identifier="MR-2024-001",
                password_hash=hash_password(patient_password),
            )
        )

        encounter = Encounter(organization_id=org.id, patient_id=patient.id, doctor_id=doctor.id)
        db.add(encounter)
        db.flush()

        case = ClinicalCase(
            organization_id=org.id,
            encounter_id=encounter.id,
            patient_id=patient.id,
            created_by=doctor.id,
            chief_complaint="Хэвлийн өвдөлт, дотор муухайрах",
            status="draft",
        )
        db.add(case)
        db.flush()

        db.add_all(
            [
                Symptom(case_id=case.id, name="Баруун дээд хэвлийн өвдөлт", severity="moderate", onset_date=date(2026, 5, 28), duration="3 хоног", note="Идсэний дараа нэмэгддэг"),
                Symptom(case_id=case.id, name="Дотор муухайрах", severity="mild", onset_date=date(2026, 5, 28), duration="3 хоног"),
                LabResult(case_id=case.id, test_name="ALT", value=120, unit="U/L", reference_low=7, reference_high=40, abnormal_flag=True, collected_at=date(2026, 5, 31)),
                LabResult(case_id=case.id, test_name="AST", value=98, unit="U/L", reference_low=10, reference_high=35, abnormal_flag=True, collected_at=date(2026, 5, 31)),
                LabResult(case_id=case.id, test_name="Билирубин", value=1.1, unit="mg/dL", reference_low=0.2, reference_high=1.2, abnormal_flag=False, collected_at=date(2026, 5, 31)),
            ]
        )

        atorvastatin = Medication(case_id=case.id, name="Atorvastatin", dose="40мг", route="амаар", frequency="Өдөрт 1 удаа", start_date=date(2025, 11, 15), status="active")
        metformin = Medication(case_id=case.id, name="Metformin", dose="500мг", route="амаар", frequency="Өдөрт 2 удаа", start_date=date(2024, 1, 10), status="active")
        atorvastatin.ingredients = [MedicationIngredient(ingredient_name="Atorvastatin calcium")]
        metformin.ingredients = [MedicationIngredient(ingredient_name="Metformin hydrochloride")]
        db.add_all([atorvastatin, metformin])
        db.add(Supplement(case_id=case.id, name="Herbal liver support", ingredients=["milk thistle"], dose="1 капсул", start_date=date(2026, 5, 1)))
        db.commit()
        print("Seed data created.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
