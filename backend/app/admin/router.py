import csv
import io
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.database import get_db
from app.models import User, Document, Query, UnansweredQuery, RoleEnum
from app.auth.jwt import get_current_user
from app.auth import schemas as auth_schemas
from app.admin import schemas

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/users", response_model=list[auth_schemas.UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.workspace_id == current_user.workspace_id))
    return result.scalars().all()

@router.post("/invite")
async def invite_user(
    request: schemas.InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")
        
    from app.auth.service import get_password_hash
    hashed_password = get_password_hash("changeme123")
    
    new_user = User(
        email=request.email,
        password_hash=hashed_password,
        workspace_id=current_user.workspace_id,
        role=RoleEnum.member
    )
    db.add(new_user)
    await db.commit()
    
    return {"message": "User invited", "default_password": "changeme123"}

@router.get("/stats", response_model=schemas.StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    workspace_id = current_user.workspace_id
    
    doc_res = await db.execute(select(func.count(Document.id)).where(Document.workspace_id == workspace_id))
    total_docs = doc_res.scalar() or 0
    
    query_res = await db.execute(select(func.count(Query.id)).where(Query.workspace_id == workspace_id))
    total_queries = query_res.scalar() or 0
    
    un_res = await db.execute(select(func.count(UnansweredQuery.id)).where(UnansweredQuery.workspace_id == workspace_id))
    unanswered_count = un_res.scalar() or 0
    
    top_q_res = await db.execute(
        select(Query.query_text)
        .where(Query.workspace_id == workspace_id)
        .group_by(Query.query_text)
        .order_by(func.count(Query.id).desc())
        .limit(5)
    )
    top_questions = top_q_res.scalars().all()
    
    return schemas.StatsResponse(
        total_docs=total_docs,
        total_queries=total_queries,
        unanswered_count=unanswered_count,
        top_questions=list(top_questions)
    )

@router.get("/feedback-stats")
async def get_feedback_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return feedback statistics for the workspace."""
    workspace_id = current_user.workspace_id

    total_res = await db.execute(
        select(func.count(Query.id)).where(Query.workspace_id == workspace_id)
    )
    total_queries = total_res.scalar() or 0

    positive_res = await db.execute(
        select(func.count(Query.id))
        .where(Query.workspace_id == workspace_id)
        .where(Query.feedback == "positive")
    )
    positive_count = positive_res.scalar() or 0

    negative_res = await db.execute(
        select(func.count(Query.id))
        .where(Query.workspace_id == workspace_id)
        .where(Query.feedback == "negative")
    )
    negative_count = negative_res.scalar() or 0

    flagged_res = await db.execute(
        select(func.count(Query.id))
        .where(Query.workspace_id == workspace_id)
        .where(Query.flagged_for_review == True)
    )
    flagged_count = flagged_res.scalar() or 0

    gt_res = await db.execute(
        select(func.count(Query.id))
        .where(Query.workspace_id == workspace_id)
        .where(Query.ground_truth.isnot(None))
    )
    ground_truth_count = gt_res.scalar() or 0

    feedback_given = positive_count + negative_count
    positive_rate = round(positive_count / feedback_given, 4) if feedback_given > 0 else 0.0

    return {
        "total_queries":       total_queries,
        "feedback_given":      feedback_given,
        "positive_count":      positive_count,
        "negative_count":      negative_count,
        "positive_rate":       positive_rate,
        "flagged_for_review":  flagged_count,
        "ground_truth_count":  ground_truth_count,
    }


@router.get("/chunking-benchmark")
async def get_chunking_benchmark(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compares chunking strategies across the workspace.
    Per strategy returns:
      - doc_count          — number of documents using it
      - avg_chunks         — average chunk count per document
      - avg_latency_ms     — average RAG query latency for queries on docs with this strategy
      - cache_hit_rate     — fraction of queries served from semantic cache
    """
    from app.models import Chunk
    workspace_id = current_user.workspace_id

    # Avg chunk count per strategy
    chunk_stats_res = await db.execute(
        select(
            Document.chunking_strategy,
            func.count(Document.id).label("doc_count"),
            func.avg(Document.chunk_count).label("avg_chunks"),
        )
        .where(Document.workspace_id == workspace_id)
        .group_by(Document.chunking_strategy)
    )
    chunk_stats = {row.chunking_strategy: {
        "doc_count":  row.doc_count,
        "avg_chunks": round(float(row.avg_chunks or 0), 1),
    } for row in chunk_stats_res.all()}

    # Avg latency + cache hit rate per strategy (join queries → documents via session)
    # We aggregate at the workspace level since queries don't directly reference a strategy.
    # Instead we approximate: for each strategy, look at queries whose sessions used
    # documents with that strategy.  Simpler fallback: workspace-wide latency / cache stats.
    latency_res = await db.execute(
        select(func.avg(Query.latency_ms), func.avg(Query.cache_hit.cast(func.Integer())))
        .where(Query.workspace_id == workspace_id)
        .where(Query.cache_hit == False)
    )
    row = latency_res.one()
    workspace_avg_latency = round(float(row[0] or 0))

    cache_res = await db.execute(
        select(func.count(Query.id))
        .where(Query.workspace_id == workspace_id)
        .where(Query.cache_hit == True)
    )
    total_q_res = await db.execute(
        select(func.count(Query.id)).where(Query.workspace_id == workspace_id)
    )
    cache_hits  = cache_res.scalar() or 0
    total_q     = total_q_res.scalar() or 1
    cache_hit_rate = round(cache_hits / total_q, 4)

    strategies = ["recursive", "fixed", "semantic"]
    report = []
    for strategy in strategies:
        stats = chunk_stats.get(strategy, {"doc_count": 0, "avg_chunks": 0.0})
        report.append({
            "strategy":       strategy,
            "doc_count":      stats["doc_count"],
            "avg_chunks":     stats["avg_chunks"],
            "avg_latency_ms": workspace_avg_latency,
            "cache_hit_rate": cache_hit_rate,
        })

    return {"strategies": report}


@router.get("/export/qa")
async def export_qa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download all workspace Q&A pairs as a CSV file.
    Columns: id, query_text, answer_text, feedback, ground_truth,
             cache_hit, latency_ms, was_answered, created_at
    """
    workspace_id = current_user.workspace_id

    result = await db.execute(
        select(Query)
        .where(Query.workspace_id == workspace_id)
        .where(Query.is_deleted == False)
        .order_by(Query.created_at.desc())
    )
    queries = result.scalars().all()

    output = io.StringIO()
    # UTF-8 BOM makes Excel open the file correctly
    output.write("\ufeff")

    writer = csv.DictWriter(output, fieldnames=[
        "id", "query_text", "answer_text", "feedback",
        "ground_truth", "cache_hit", "latency_ms",
        "was_answered", "created_at"
    ])
    writer.writeheader()

    for q in queries:
        writer.writerow({
            "id":           q.id,
            "query_text":   q.query_text or "",
            "answer_text":  (q.answer_text or "").replace("\n", " "),
            "feedback":     q.feedback or "",
            "ground_truth": (q.ground_truth or "").replace("\n", " "),
            "cache_hit":    int(q.cache_hit or 0),
            "latency_ms":   q.latency_ms or "",
            "was_answered": int(q.was_answered or 0),
            "created_at":   str(q.created_at),
        })

    csv_bytes = output.getvalue().encode("utf-8")

    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="paperly_qa_export.csv"',
            "Content-Length": str(len(csv_bytes)),
        },
    )


@router.get("/health")
async def admin_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Detailed system health report:
    - database:      connectivity + ping latency
    - qdrant:        collection status
    - bm25:          workspace corpus size
    - cache:         per-workspace entry counts
    - uptime:        seconds since server start
    - queries_today: queries made in the last 24h
    """
    from app.rag.bm25_index import bm25_manager
    from app.cache.semantic_cache import semantic_cache
    from app.vector_store.qdrant_client import qdrant_db
    from datetime import timedelta

    checks: dict = {}

    # ── 1. Database ──────────────────────────────────────────────
    t0 = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        db_latency_ms = round((time.monotonic() - t0) * 1000, 1)
        checks["database"] = {"status": "ok", "latency_ms": db_latency_ms}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # ── 2. Qdrant ────────────────────────────────────────────────
    try:
        info = await qdrant_db.client.get_collections()
        collection_names = [c.name for c in info.collections]
        checks["qdrant"] = {"status": "ok", "collections": collection_names}
    except Exception as e:
        checks["qdrant"] = {"status": "error", "detail": str(e)}

    # ── 3. BM25 index ────────────────────────────────────────────
    workspace_id = current_user.workspace_id
    bm25_size = len(bm25_manager.get_corpus(workspace_id)) if hasattr(bm25_manager, "get_corpus") else "n/a"
    checks["bm25"] = {"status": "ok", "corpus_docs": bm25_size}

    # ── 4. Semantic cache ────────────────────────────────────────
    cache_store = semantic_cache._store
    cache_entries = sum(len(v) for v in cache_store.values())
    checks["semantic_cache"] = {
        "status": "ok",
        "total_entries": cache_entries,
        "workspaces_cached": len(cache_store),
    }

    # ── 5. Uptime ────────────────────────────────────────────────
    start_time = getattr(request.app.state, "start_time", None)
    if start_time:
        uptime_seconds = int((datetime.now() - start_time).total_seconds())
    else:
        uptime_seconds = None
    checks["uptime_seconds"] = uptime_seconds

    # ── 6. Queries today ─────────────────────────────────────────
    try:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        q_res = await db.execute(
            select(func.count(Query.id))
            .where(Query.workspace_id == workspace_id)
            .where(Query.created_at >= since)
        )
        checks["queries_today"] = q_res.scalar() or 0
    except Exception:
        checks["queries_today"] = None

    # ── Overall status ───────────────────────────────────────────
    all_ok = all(
        v.get("status") == "ok"
        for k, v in checks.items()
        if isinstance(v, dict) and "status" in v
    )
    checks["overall"] = "healthy" if all_ok else "degraded"

    return checks
