import asyncio
from typing import List
import httpx
from app.config import settings

# This API key only supports v1beta embedding models
_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
_BATCH_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents"


class GeminiEmbedder:
    def __init__(self):
        self._api_key = settings.GEMINI_API_KEY

    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text via direct REST API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _EMBED_URL,
                headers={"x-goog-api-key": self._api_key},
                json={
                    "model": "models/gemini-embedding-001",
                    "content": {"parts": [{"text": text}]}
                }
            )
            if not resp.is_success:
                raise RuntimeError(
                    f"Gemini embed_text failed ({resp.status_code}): {resp.text}"
                )
            return resp.json()["embedding"]["values"]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embed texts."""
        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            requests_payload = [
                {
                    "model": "models/gemini-embedding-001",
                    "content": {"parts": [{"text": t}]}
                }
                for t in batch
            ]
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    _BATCH_URL,
                    headers={"x-goog-api-key": self._api_key},
                    json={"requests": requests_payload}
                )
                if not resp.is_success:
                    raise RuntimeError(
                        f"Gemini embed_batch failed ({resp.status_code}): {resp.text}"
                    )
                data = resp.json()
                embeddings = [e["values"] for e in data["embeddings"]]
                all_embeddings.extend(embeddings)

            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)

        return all_embeddings


embedder = GeminiEmbedder()
