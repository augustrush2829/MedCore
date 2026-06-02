# MedCore Medical Knowledge Base

Add local clinical knowledge files here (`.md`, `.txt`, `.json`, `.pdf`) and run:

```bash
cd backend
python -m app.scripts.ingest_knowledge
```

The ingest script chunks documents, creates Gemini embeddings when `GEMINI_API_KEY` is set, and stores them in the backend database for RAG analysis.
