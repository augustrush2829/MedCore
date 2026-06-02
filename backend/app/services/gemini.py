import json
import urllib.error
import urllib.request

from app.core.config import get_settings


API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def gemini_configured() -> bool:
    return bool(get_settings().gemini_api_key)


def generate_json(
    prompt: str,
    *,
    system_instruction: str | None = None,
    image: dict | None = None,
    timeout_seconds: int = 60,
) -> dict:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY тохируулагдаагүй байна")

    parts: list[dict] = [{"text": prompt}]
    if image:
        parts.append({"inlineData": {"mimeType": image["mime_type"], "data": image["base64"]}})
    body: dict = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    data = _post_json(
        f"{API_BASE}/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}",
        body,
        timeout_seconds=timeout_seconds,
    )
    text = "".join(part.get("text", "") for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))
    if not text:
        raise RuntimeError("Gemini хоосон хариу буцаалаа")
    return _parse_json_text(text)


def embed_text(text: str) -> list[float]:
    settings = get_settings()
    if not settings.gemini_api_key:
        return lexical_embedding(text)
    data = _post_json(
        f"{API_BASE}/models/{settings.gemini_embedding_model}:embedContent?key={settings.gemini_api_key}",
        {"content": {"parts": [{"text": text[:12000]}]}},
        timeout_seconds=45,
    )
    values = data.get("embedding", {}).get("values")
    if not isinstance(values, list) or not values:
        raise RuntimeError("Gemini embedding хоосон хариу буцаалаа")
    return [float(value) for value in values]


def lexical_embedding(text: str, dimensions: int = 384) -> list[float]:
    vector = [0.0] * dimensions
    for token in text.lower().replace("/", " ").replace("-", " ").split():
        index = hash(token) % dimensions
        vector[index] += 1.0
    magnitude = sum(value * value for value in vector) ** 0.5
    if magnitude:
        vector = [value / magnitude for value in vector]
    return vector


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
        raise RuntimeError(f"Gemini API алдаа {exc.code}: {detail}") from exc


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
