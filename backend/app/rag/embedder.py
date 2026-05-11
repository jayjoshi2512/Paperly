import asyncio
from typing import List
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings

# Configure API key
genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiEmbedder:
    def __init__(self):
        self.model = "models/text-embedding-004"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text with retry."""
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embed with rate limiting (max 100/call)."""
        all_embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self._embed_batch_internal(batch)
            all_embeddings.extend(embeddings)
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1) # 100ms delay between batches
                
        return all_embeddings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _embed_batch_internal(self, texts: List[str]) -> List[List[float]]:
        result = genai.embed_content(
            model=self.model,
            content=texts,
            task_type="retrieval_document"
        )
        return result['embedding']

embedder = GeminiEmbedder()
