import json
import asyncio
from typing import AsyncGenerator, List
import httpx
from app.config import settings
from app.rag.reranker import RerankedChunk

# Groq is OpenAI-compatible — ultra-fast inference, 30 RPM / 14,400 RPD free tier
_GROQ_BASE = "https://api.groq.com/openai/v1"
_MODEL = "llama-3.3-70b-versatile"  # fast, high quality, generous limits


class GroqGenerator:
    def __init__(self):
        self._api_key = settings.GROQ_API_KEY

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(self, query: str, context_chunks: List[RerankedChunk], chat_history: List[dict] = None) -> list:
        context_str = ""
        for chunk in context_chunks:
            context_str += f"[File: {chunk.filename}, Page {chunk.page_number}]: {chunk.text}\n\n"

        system = (
            "You are a helpful assistant for internal company knowledge. "
            "Answer ONLY based on the provided context. "
            "If the answer is not in the context, say: "
            "'I don't have information about this in the uploaded documents.' "
            "Always cite the source filename and page number for each fact you state. "
            "Use the chat history for context, but base factual answers on the provided context."
        )
        user = f"Context:\n{context_str}\n\nQuestion: {query}"
        
        msgs = [{"role": "system", "content": system}]
        if chat_history:
            msgs.extend(chat_history)
            
        msgs.append({"role": "user", "content": user})
        return msgs

    def _make_payload(self, query: str, context_chunks: List[RerankedChunk], chat_history: List[dict] = None, stream: bool = False) -> dict:
        return {
            "model": _MODEL,
            "messages": self._build_messages(query, context_chunks, chat_history),
            "temperature": 0.2,
            "max_tokens": 2048,
            "stream": stream,
        }

    async def generate(self, query: str, context_chunks: List[RerankedChunk], chat_history: List[dict] = None) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_GROQ_BASE}/chat/completions",
                headers=self._headers(),
                json=self._make_payload(query, context_chunks, chat_history, stream=False),
            )
            if not resp.is_success:
                raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:300]}")
            return resp.json()["choices"][0]["message"]["content"]

    async def stream_generate(self, query: str, context_chunks: List[RerankedChunk], chat_history: List[dict] = None) -> AsyncGenerator[str, None]:
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        f"{_GROQ_BASE}/chat/completions",
                        headers=self._headers(),
                        json=self._make_payload(query, context_chunks, chat_history, stream=True),
                    ) as resp:
                        if not resp.is_success:
                            body = await resp.aread()
                            raise RuntimeError(f"Groq API error {resp.status_code}: {body.decode()[:300]}")

                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            raw = line[6:].strip()
                            if raw == "[DONE]":
                                return
                            try:
                                data = json.loads(raw)
                                delta = data["choices"][0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    yield text
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                        return  # success
            except httpx.ConnectError:
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                raise RuntimeError("Cannot connect to Groq API. Check your internet connection.")

    async def condense_query(self, query: str, chat_history: List[dict]) -> str:
        if not chat_history:
            return query
            
        system = (
            "Given a chat history and the latest user question which might reference context in the chat history, "
            "formulate a standalone question which can be understood without the chat history. "
            "Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
        )
        
        msgs = [{"role": "system", "content": system}]
        msgs.extend(chat_history)
        msgs.append({"role": "user", "content": query})
        
        payload = {
            "model": _MODEL,
            "messages": msgs,
            "temperature": 0.1,
            "max_tokens": 512,
            "stream": False,
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{_GROQ_BASE}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            if not resp.is_success:
                return query  # fallback to original query
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def summarize_session(self, current_summary: str, recent_exchanges: List[dict]) -> str:
        system = (
            "You are an AI tasked with maintaining a running summary of a user's session state. "
            "Given the current summary state and the most recent 5 chat exchanges, output an updated, concise summary. "
            "Focus strictly on: 1) The user's core intent. 2) Key entities/topics discussed. 3) Any explicitly stated preferences. "
            "Keep the summary to a single short paragraph. Do not include conversational filler."
        )
        
        exchanges_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_exchanges])
        user = f"Current Summary:\n{current_summary or 'None'}\n\nRecent Exchanges:\n{exchanges_str}\n\nUpdated Summary:"
        
        payload = {
            "model": _MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.2,
            "max_tokens": 512,
            "stream": False,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_GROQ_BASE}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            if not resp.is_success:
                return current_summary
            return resp.json()["choices"][0]["message"]["content"].strip()


generator = GroqGenerator()
