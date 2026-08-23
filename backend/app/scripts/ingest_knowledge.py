from pathlib import Path

from app.db.session import Base, SessionLocal, engine
from app.services.knowledge import ingest_knowledge_path


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        root = Path(__file__).resolve().parents[3] / "data" / "medical_kb"
        root.mkdir(parents=True, exist_ok=True)
        result = ingest_knowledge_path(db, root)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
