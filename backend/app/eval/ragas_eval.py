import logging
from typing import List
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

from app.models import Query

logger = logging.getLogger(__name__)

@dataclass
class EvalResult:
    query_id: str
    faithfulness: float
    relevancy: float

async def run_ragas_evaluation(db: AsyncSession, query_ids: List[str], workspace_id: str) -> dict:
    result = await db.execute(
        select(Query).where(Query.id.in_(query_ids), Query.workspace_id == workspace_id)
    )
    queries = result.scalars().all()
    
    if not queries:
        return {"error": "No queries found"}

    dataset_dict = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [] 
    }
    
    valid_queries = []
    for q in queries:
        if not q.retrieved_chunk_ids:
            continue
            
        contexts = [chunk.get("text", "") for chunk in q.retrieved_chunk_ids]
        
        dataset_dict["question"].append(q.query_text)
        dataset_dict["answer"].append(q.answer_text)
        dataset_dict["contexts"].append(contexts)
        dataset_dict["ground_truth"].append(q.answer_text) # Dummy ground truth
        valid_queries.append(q)

    if not dataset_dict["question"]:
        return {"error": "No valid contexts found"}

    ds = Dataset.from_dict(dataset_dict)
    
    try:
        score = evaluate(ds, metrics=[
            faithfulness, answer_relevancy, context_precision, context_recall
        ])
    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}")
        return {"error": str(e)}

    df = score.to_pandas()
    
    results = []
    for idx, row in df.iterrows():
        q = valid_queries[idx]
        f_score = float(row.get("faithfulness", 0.0) or 0.0)
        r_score = float(row.get("answer_relevancy", 0.0) or 0.0)
        
        q.faithfulness_score = f_score
        q.relevancy_score = r_score
        
        results.append({
            "query_id": q.id,
            "faithfulness": f_score,
            "relevancy": r_score,
            "context_precision": float(row.get("context_precision", 0.0) or 0.0),
            "context_recall": float(row.get("context_recall", 0.0) or 0.0)
        })
        
    await db.commit()
    
    return {
        "aggregate": {
            "faithfulness": float(df["faithfulness"].mean()) if "faithfulness" in df else 0.0,
            "relevancy": float(df["answer_relevancy"].mean()) if "answer_relevancy" in df else 0.0
        },
        "per_query": results
    }
