from dataclasses import dataclass
from typing import List
import hashlib
import cohere
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.rag.retrieval import RetrievedChunk

@dataclass
class RerankedChunk(RetrievedChunk):
    rerank_score: float

class CohereReranker:
    def __init__(self):
        self.client = cohere.Client(api_key=settings.COHERE_API_KEY)
        self._cache = {} # MD5 -> results
        self.max_cache_size = 256

    def _get_cache_key(self, query: str, chunk_ids: List[str]) -> str:
        s = query + "".join(sorted(chunk_ids))
        return hashlib.md5(s.encode()).hexdigest()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _call_cohere(self, query: str, documents: List[str], top_n: int):
        return self.client.rerank(
            query=query,
            documents=documents,
            model="rerank-english-v3.0",
            top_n=top_n
        )

    def rerank(self, query: str, chunks: List[RetrievedChunk], top_n: int = 5) -> List[RerankedChunk]:
        if not chunks:
            return []
            
        chunk_ids = [c.chunk_id for c in chunks]
        cache_key = self._get_cache_key(query, chunk_ids)
        
        if cache_key in self._cache:
            return self._cache[cache_key][:top_n]
            
        documents = [c.text for c in chunks]
        response = self._call_cohere(query, documents, top_n)
        
        reranked = []
        for res in response.results:
            orig_chunk = chunks[res.index]
            reranked.append(RerankedChunk(
                chunk_id=orig_chunk.chunk_id,
                document_id=orig_chunk.document_id,
                filename=orig_chunk.filename,
                text=orig_chunk.text,
                page_number=orig_chunk.page_number,
                dense_score=orig_chunk.dense_score,
                sparse_score=orig_chunk.sparse_score,
                fused_score=orig_chunk.fused_score,
                rerank_score=res.relevance_score
            ))
            
        # Manage cache
        if len(self._cache) >= self.max_cache_size:
            # Simple eviction
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = reranked
        
        return reranked

reranker = CohereReranker()
