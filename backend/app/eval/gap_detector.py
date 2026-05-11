import google.generativeai as genai
from typing import List, Dict
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sklearn.cluster import KMeans
import numpy as np

from app.models import UnansweredQuery
from app.rag.embedder import embedder
from app.config import settings

class GapCluster(BaseModel):
    cluster_id: int
    representative_query: str
    count: int
    suggested_doc_title: str
    query_examples: List[str]

async def detect_knowledge_gaps(db: AsyncSession, workspace_id: str) -> List[GapCluster]:
    result = await db.execute(
        select(UnansweredQuery).where(UnansweredQuery.workspace_id == workspace_id)
    )
    queries = result.scalars().all()
    
    if not queries:
        return []
        
    texts = [q.query_text for q in queries]
    
    if len(texts) < 5:
        # Not enough data to cluster meaningfully
        return [GapCluster(
            cluster_id=0,
            representative_query=texts[0],
            count=len(texts),
            suggested_doc_title="Uncategorized missing knowledge",
            query_examples=texts
        )]
        
    # Embed
    embeddings = await embedder.embed_batch(texts)
    X = np.array(embeddings)
    
    # Auto-determine k (max 5, min 2)
    k = min(5, len(texts) // 2)
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    
    # Process clusters
    clusters: Dict[int, List[str]] = {i: [] for i in range(k)}
    for label, text in zip(labels, texts):
        clusters[label].append(text)
        
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    gap_clusters = []
    for cluster_id, cluster_texts in clusters.items():
        if not cluster_texts:
            continue
            
        prompt = f"""
        Users are asking the following questions, but the system doesn't have the answers in its knowledge base:
        {chr(10).join(cluster_texts[:5])}
        
        Generate a short, professional title for a document (SOP, policy, or guide) that should be written to answer these questions.
        Return ONLY the title, no quotes or explanation.
        """
        response = await model.generate_content_async(prompt)
        suggested_title = response.text.strip()
        
        gap_clusters.append(GapCluster(
            cluster_id=int(cluster_id),
            representative_query=cluster_texts[0],
            count=len(cluster_texts),
            suggested_doc_title=suggested_title,
            query_examples=cluster_texts[:5]
        ))
        
    return gap_clusters
