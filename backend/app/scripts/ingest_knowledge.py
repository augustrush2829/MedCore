from pathlib import Path

from app.db.session import Base, SessionLocal, engine
from app.services.knowledge import ingest_knowledge_path


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        data_root = Path(__file__).resolve().parents[3] / "data"
        medical_kb = data_root / "medical_kb"
        medical_kb.mkdir(parents=True, exist_ok=True)
        for root, category in [(medical_kb, "clinical"), (data_root / "mn_edoctor_kb", "clinical")]:
            if not root.exists():
                continue
            result = ingest_knowledge_path(db, root, category=category)
            print(f"{root}: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
