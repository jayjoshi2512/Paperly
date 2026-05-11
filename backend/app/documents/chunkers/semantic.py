from typing import List
from langchain_experimental.text_splitter import SemanticChunker as LCSemanticChunker
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings
from .base import BaseChunker

class SemanticChunker(BaseChunker):
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.GEMINI_API_KEY
        )
        self.splitter = LCSemanticChunker(
            self.embeddings, 
            breakpoint_threshold_type="percentile"
        )

    def chunk(self, text: str) -> List[str]:
        if not text.strip():
            return []
        docs = self.splitter.create_documents([text])
        return [doc.page_content for doc in docs]
