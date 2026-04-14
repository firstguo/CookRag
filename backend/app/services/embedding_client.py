from __future__ import annotations

from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings


class OllamaEmbeddingClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=3.0))
    async def embed(self, text: str) -> List[float]:
        url = f"{self._settings.OLLAMA_HOST.rstrip('/')}/api/embeddings"
        payload = {
            "model": self._settings.OLLAMA_EMBEDDING_MODEL,
            "prompt": text,
        }
        timeout = httpx.Timeout(self._settings.OLLAMA_TIMEOUT_S)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        embedding = data.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise RuntimeError("Ollama response missing embedding")
        return [float(x) for x in embedding]

