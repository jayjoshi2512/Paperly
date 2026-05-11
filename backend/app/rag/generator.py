import json
import asyncio
from typing import AsyncGenerator, List
import httpx
from app.config import settings
from app.rag.reranker import RerankedChunk

_MODEL = "gemini-2.0-flash"
_GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"
_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:streamGenerateContent"


def _raise_for_gemini(status_code: int, body: str = ""):
    if status_code == 429:
        raise RuntimeError("Gemini API rate limit hit. Please wait ~1 minute and try again.")
    if status_code == 503:
        raise RuntimeError("Gemini API is temporarily overloaded. Please try again in a few seconds.")
    if status_code >= 400:
        raise RuntimeError(f"Gemini API error {status_code}: {body[:200]}")


class GeminiGenerator:
    def __init__(self):
        self._api_key = settings.GEMINI_API_KEY

    def _build_prompt(self, query: str, context_chunks: List[RerankedChunk]) -> str:
        context_str = ""
        for chunk in context_chunks:
            context_str += f"[Doc ID: {chunk.document_id}, Page {chunk.page_number}]: {chunk.text}\n\n"
        return f"""You are a helpful assistant for internal company knowledge.
Answer ONLY based on the provided context. If the answer is not in the context, say "I don't have information about this in the uploaded documents."

Context:
{context_str}

Question: {query}

Answer clearly and cite the source document ID and page number for each fact."""

    def _make_payload(self, prompt: str) -> dict:
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        }

    async def generate(self, query: str, context_chunks: List[RerankedChunk]) -> str:
        prompt = self._build_prompt(query, context_chunks)
        # 2 fast retries (0s, 3s) then fail — no long waits
        for attempt in range(3):
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    _GENERATE_URL,
                    headers={"x-goog-api-key": self._api_key},
                    json=self._make_payload(prompt),
                )
                if resp.status_code in (503, 500) and attempt < 2:
                    await asyncio.sleep(3)
                    continue
                _raise_for_gemini(resp.status_code, resp.text)
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        raise RuntimeError("Gemini API unavailable. Please try again in a moment.")

    async def stream_generate(self, query: str, context_chunks: List[RerankedChunk]) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(query, context_chunks)
        payload = self._make_payload(prompt)

        # 2 fast retries for transient errors
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        _STREAM_URL + "?alt=sse",
                        headers={"x-goog-api-key": self._api_key},
                        json=payload,
                    ) as resp:
                        if resp.status_code in (503, 500) and attempt < 2:
                            await asyncio.sleep(3)
                            continue
                        _raise_for_gemini(resp.status_code)
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            raw = line[6:].strip()
                            if raw == "[DONE]":
                                return
                            try:
                                data = json.loads(raw)
                                for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                                    if part.get("text"):
                                        yield part["text"]
                            except (json.JSONDecodeError, IndexError, KeyError):
                                continue
                        return  # success
            except httpx.ConnectError:
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                raise RuntimeError("Cannot connect to Gemini API. Check your internet connection.")

        raise RuntimeError("Gemini API unavailable after retries. Please try again shortly.")


generator = GeminiGenerator()
