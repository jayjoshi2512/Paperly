import asyncio
from typing import List
import httpx
from app.config import settings

# Cohere embed-english-v3.0: 1024 dimensions, generous free tier
_COHERE_EMBED_URL = "https://api.cohere.com/v2/embed"
_EMBED_MODEL = "embed-english-v3.0"
EMBEDDING_DIMENSION = 1024


class CohereEmbedder:
    def __init__(self):
        self._api_key = settings.COHERE_API_KEY

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text using Cohere."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embed texts using Cohere (max 96 per request on free tier)."""
        all_embeddings = []
        batch_size = 96

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    _COHERE_EMBED_URL,
                    headers=self._headers(),
                    json={
                        "model": _EMBED_MODEL,
                        "texts": batch,
                        "input_type": "search_document",
                        "embedding_types": ["float"],
                    }
                )
                if not resp.is_success:
                    raise RuntimeError(
                        f"Cohere embed failed ({resp.status_code}): {resp.text[:300]}"
                    )
                data = resp.json()
                # v2 API returns embeddings.float as list of lists
                batch_embeddings = data["embeddings"]["float"]
                all_embeddings.extend(batch_embeddings)

            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)  # be nice to the API

        return all_embeddings

    async def embed_query(self, text: str) -> List[float]:
        """Embed a search query (different input_type from documents)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _COHERE_EMBED_URL,
                headers=self._headers(),
                json={
                    "model": _EMBED_MODEL,
                    "texts": [text],
                    "input_type": "search_query",
                    "embedding_types": ["float"],
                }
            )
            if not resp.is_success:
                raise RuntimeError(
                    f"Cohere embed_query failed ({resp.status_code}): {resp.text[:300]}"
                )
            return resp.json()["embeddings"]["float"][0]


embedder = CohereEmbedder()
