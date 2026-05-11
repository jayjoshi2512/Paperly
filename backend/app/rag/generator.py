import json
from typing import AsyncGenerator, List
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.rag.reranker import RerankedChunk

genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiGenerator:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def _build_prompt(self, query: str, context_chunks: List[RerankedChunk]) -> str:
        context_str = ""
        for i, chunk in enumerate(context_chunks):
            context_str += f"[Doc ID: {chunk.document_id}, Page {chunk.page_number}]: {chunk.text}\n\n"
            
        prompt = f"""
        You are a helpful assistant for internal company knowledge.
        Answer ONLY based on the provided context. If the answer is not in the context,
        say "I don't have information about this in the uploaded documents."

        Context:
        {context_str}

        Question: {query}

        Provide a clear answer and cite the source document ID and page number for each fact.
        """
        return prompt

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate(self, query: str, context_chunks: List[RerankedChunk]) -> str:
        prompt = self._build_prompt(query, context_chunks)
        response = await self.model.generate_content_async(prompt)
        return response.text

    async def stream_generate(self, query: str, context_chunks: List[RerankedChunk]) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(query, context_chunks)
        response = await self.model.generate_content_async(prompt, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text

generator = GeminiGenerator()
