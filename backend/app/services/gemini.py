import json
import urllib.error
import urllib.request
from functools import lru_cache

from app.core.config import get_settings


def gemini_configured() -> bool:
    return bool(get_settings().gemini_api_key)


def generate_json(
    prompt: str,
    *,
    system_instruction: str | None = None,
    image: dict | None = None,
    timeout_seconds: int = 120,
) -> dict:
    """Run a local Ollama model and parse its response as JSON.

    Model selection: the vision model handles requests that include an image
    (lab-photo OCR); the text model handles everything else (RAG synthesis).
    """
    settings = get_settings()
    model = settings.ollama_vision_model if image else settings.ollama_model

    body: dict = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if system_instruction:
        body["system"] = system_instruction
    if image:
        body["images"] = [image["base64"]]

    data = _post_json(
        f"{settings.ollama_base_url}/api/generate",
        body,
        timeout_seconds=timeout_seconds,
    )
    text = data.get("response", "")
    if not text:
        raise RuntimeError("Ollama хоосон хариу буцаалаа")
    return _parse_json_text(text)


@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embedding_model_name)


def embed_text(text: str, *, is_query: bool = False) -> list[float]:
    """Embed text in-process with the local sentence-transformers model.

    multilingual-e5-base expects a "query: " / "passage: " instruction
    prefix on its input to produce well-separated retrieval embeddings.
    """
    prefix = "query: " if is_query else "passage: "
    vector = _embedding_model().encode(prefix + text[:12000], normalize_embeddings=True)
    return vector.tolist()


def _post_json(url: str, body: dict, *, timeout_seconds: int) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Ollama API алдаа {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama сервертэй холбогдож чадсангүй ({url}): {exc.reason}") from exc


def _parse_json_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        first = cleaned.find("{")
        last = cleaned.rfind("}")
        if first >= 0 and last > first:
            return json.loads(cleaned[first:last + 1])
        raise
