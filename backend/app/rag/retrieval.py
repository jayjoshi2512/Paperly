from dataclasses import dataclass
from typing import List, Dict
from app.rag.embedder import embedder
from app.vector_store.qdrant_client import qdrant_db
from app.rag.bm25_index import bm25_manager
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models import Chunk

@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    page_number: int
    dense_score: float
    sparse_score: float
    fused_score: float

async def hybrid_search(query: str, workspace_id: str, top_k: int = 20) -> List[RetrievedChunk]:
    query_embedding = await embedder.embed_text(query)
    dense_results = await qdrant_db.search(query_embedding, workspace_id, top_k=top_k)
    sparse_scores = bm25_manager.get_scores(workspace_id, query, top_k=top_k)
    
    dense_map = {r.chunk_id: r for r in dense_results}
    sparse_map = {cid: score for cid, score in sparse_scores}
    
    all_chunk_ids = set(dense_map.keys()).union(sparse_map.keys())
    missing_cids = [cid for cid in sparse_map if cid not in dense_map]
    
    metadata_map = {}
    if missing_cids:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Chunk).where(Chunk.id.in_(missing_cids)))
            for c in result.scalars().all():
                metadata_map[c.id] = {
                    "document_id": c.document_id,
                    "page_number": c.page_number or 1,
                    "text": c.chunk_text
                }
                
    # Reciprocal Rank Fusion
    k = 60
    rrf_scores: Dict[str, float] = {}
    
    # Rank dense
    dense_sorted = sorted(dense_results, key=lambda x: x.score, reverse=True)
    for rank, item in enumerate(dense_sorted):
        rrf_scores[item.chunk_id] = rrf_scores.get(item.chunk_id, 0) + 1.0 / (k + rank + 1)
        
    # Rank sparse
    sparse_sorted = sorted(sparse_scores, key=lambda x: x[1], reverse=True)
    for rank, (cid, score) in enumerate(sparse_sorted):
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1.0 / (k + rank + 1)
        
    # Combine and sort
    fused_sorted = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    final_results = []
    for cid, fused_score in fused_sorted:
        d_score = dense_map[cid].score if cid in dense_map else 0.0
        s_score = sparse_map.get(cid, 0.0)
        
        if cid in dense_map:
            meta = dense_map[cid]
            doc_id = meta.document_id
            page_num = meta.page_number
            text = meta.text
        else:
            meta = metadata_map.get(cid, {})
            doc_id = meta.get("document_id", "")
            page_num = meta.get("page_number", 1)
            text = meta.get("text", "")
            
        final_results.append(RetrievedChunk(
            chunk_id=cid,
            document_id=doc_id,
            text=text,
            page_number=page_num,
            dense_score=d_score,
            sparse_score=s_score,
            fused_score=fused_score
        ))
        
    return final_results
