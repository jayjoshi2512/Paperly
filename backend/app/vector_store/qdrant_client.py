from typing import List
import asyncio
from qdrant_client import QdrantClient, AsyncQdrantClient
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

def _get_vector_size(info) -> int:
    """Safely extract vector size from CollectionInfo regardless of API version."""
    try:
        vectors = info.config.params.vectors
        if hasattr(vectors, "size"):
            return vectors.size  # VectorParams directly
        elif isinstance(vectors, dict):
            return list(vectors.values())[0].size  # named vectors dict
    except Exception:
        pass
    return 0  # unknown — force recreate


class PaperlyQdrant:
    def __init__(self):
        url = settings.QDRANT_URL
        self._is_local = not (url.startswith("http://") or url.startswith("https://"))
        if self._is_local:
            # Use sync client for local/SQLite mode — safer on Windows event loops
            self._sync_client = QdrantClient(path=url)
            self._async_client = None
        else:
            self._sync_client = None
            self._async_client = AsyncQdrantClient(url=url)
        self.collection_name = "paperly_chunks"
        self._collection_ready = False

    async def _run(self, fn, *args, **kwargs):
        """Run sync or async client method uniformly."""
        if self._is_local:
            return await asyncio.to_thread(fn, *args, **kwargs)
        return await fn(*args, **kwargs)

    async def setup_collection(self):
        """Creates (or recreates) the collection with correct vector size."""
        if self._collection_ready:
            return
        target_size = 1024  # Cohere embed-english-v3.0

        if self._is_local:
            client = self._sync_client
            collections = await asyncio.to_thread(client.get_collections)
            exists = any(c.name == self.collection_name for c in collections.collections)

            if exists:
                # Check dimension matches — recreate if stale
                info = await asyncio.to_thread(client.get_collection, self.collection_name)
                actual_size = _get_vector_size(info)
                if actual_size != target_size:
                    logger.warning(
                        f"Qdrant collection has size={actual_size}, expected {target_size}. Recreating."
                    )
                    await asyncio.to_thread(client.delete_collection, self.collection_name)
                    exists = False

            if not exists:
                logger.info(f"Creating Qdrant collection '{self.collection_name}' (size={target_size})")
                await asyncio.to_thread(
                    client.create_collection,
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(size=target_size, distance=qmodels.Distance.COSINE)
                )
                await asyncio.to_thread(
                    client.create_payload_index,
                    collection_name=self.collection_name,
                    field_name="workspace_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )
        else:
            client = self._async_client
            collections = await client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)

            if exists:
                info = await client.get_collection(self.collection_name)
                actual_size = _get_vector_size(info)
                if actual_size != target_size:
                    logger.warning(
                        f"Qdrant collection has size={actual_size}, expected {target_size}. Recreating."
                    )
                    await client.delete_collection(self.collection_name)
                    exists = False

            if not exists:
                logger.info(f"Creating Qdrant collection '{self.collection_name}' (size={target_size})")
                await client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(size=target_size, distance=qmodels.Distance.COSINE)
                )
                await client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="workspace_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )

        self._collection_ready = True


    async def upsert(self, points: List[qmodels.PointStruct]):
        """Batch upsert points."""
        if not points:
            return
        await self.setup_collection()
        if self._is_local:
            await asyncio.to_thread(
                self._sync_client.upsert,
                collection_name=self.collection_name,
                points=points
            )
        else:
            await self._async_client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    async def search(self, embedding: List[float], workspace_id: str, top_k: int = 20) -> List[ScoredPoint]:
        """Search points filtered by workspace."""
        await self.setup_collection()
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="workspace_id",
                    match=qmodels.MatchValue(value=workspace_id)
                )
            ]
        )
        if self._is_local:
            results = await asyncio.to_thread(
                self._sync_client.search,
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True
            )
        else:
            results = await self._async_client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True
            )

        return [
            ScoredPoint(
                chunk_id=r.payload.get("chunk_id"),
                document_id=r.payload.get("document_id"),
                page_number=r.payload.get("page_number", 0),
                text=r.payload.get("text", ""),
                score=r.score
            ) for r in results
        ]

    async def delete_by_document_id(self, document_id: str):
        """Delete all vectors for a given document."""
        await self.setup_collection()
        points_selector = qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id)
                    )
                ]
            )
        )
        if self._is_local:
            await asyncio.to_thread(
                self._sync_client.delete,
                collection_name=self.collection_name,
                points_selector=points_selector
            )
        else:
            await self._async_client.delete(
                collection_name=self.collection_name,
                points_selector=points_selector
            )

# Singleton instance
qdrant_db = PaperlyQdrant()
