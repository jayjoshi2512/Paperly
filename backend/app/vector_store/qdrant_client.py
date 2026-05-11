from typing import List
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from pydantic import BaseModel
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings

logger = logging.getLogger(__name__)

class ScoredPoint(BaseModel):
    chunk_id: str
    document_id: str
    page_number: int
    text: str
    score: float

class PaperlyQdrant:
    def __init__(self):
        self.client = AsyncQdrantClient(url=settings.QDRANT_URL)
        self.collection_name = "paperly_chunks"

    async def setup_collection(self):
        """Creates the collection if it does not exist (768-dim for text-embedding-004, Cosine)."""
        collections = await self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)
        if not exists:
            logger.info(f"Creating Qdrant collection: {self.collection_name}")
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=768,
                    distance=qmodels.Distance.COSINE
                )
            )
            # Create payload index for workspace_id to filter efficiently
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="workspace_id",
                field_schema=qmodels.PayloadSchemaType.KEYWORD
            )
            
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upsert(self, points: List[qmodels.PointStruct]):
        """Batch upsert points with retry."""
        if not points:
            return
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    async def search(self, embedding: List[float], workspace_id: str, top_k: int = 20) -> List[ScoredPoint]:
        """Search points filtered by workspace."""
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=top_k,
            query_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="workspace_id",
                        match=qmodels.MatchValue(value=workspace_id)
                    )
                ]
            ),
            with_payload=True
        )
        
        scored_points = []
        for r in results:
            scored_points.append(ScoredPoint(
                chunk_id=r.payload.get("chunk_id"),
                document_id=r.payload.get("document_id"),
                page_number=r.payload.get("page_number", 0),
                text=r.payload.get("text", ""),
                score=r.score
            ))
        return scored_points

    async def delete_by_document_id(self, document_id: str):
        """Delete all vectors for a given document."""
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id)
                        )
                    ]
                )
            )
        )

# Singleton instance
qdrant_db = PaperlyQdrant()
