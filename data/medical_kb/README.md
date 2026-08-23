# MedCore Medical Knowledge Base

Add local clinical knowledge files here (`.md`, `.txt`, `.json`, `.pdf`), or to `data/mn_edoctor_kb/`, and run:

```bash
cd backend
python -m app.scripts.ingest_knowledge
```

The ingest script chunks documents (one chunk per record for a JSON file containing a list of objects, e.g. `mn_edoctor_kb/edoctor_clean.json`; otherwise by character count), embeds each chunk in-process with the local `intfloat/multilingual-e5-base` model, and stores them in the backend database for RAG analysis. No external API key is required. Already-ingested files (matched by content hash) are skipped, so re-running the script after adding new files only ingests what's new.
