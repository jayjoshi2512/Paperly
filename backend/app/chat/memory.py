import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Query, ChatSession
from app.rag.embedder import embedder
from app.vector_store.qdrant_client import qdrant_db
from app.rag.generator import generator
from app.database import AsyncSessionLocal
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)

async def run_memory_cleanup(session_id: str, query_id: str, workspace_id: str, user_id: str):
    """Background task to run Level 2 and Level 3 memory updates."""
    if not session_id:
        return
        
    try:
        async with AsyncSessionLocal() as db:
            # 1. Level 2: Semantic Memory (Embed and save the new exchange)
            result = await db.execute(select(Query).where(Query.id == query_id))
            q = result.scalar_one_or_none()
            if q and q.answer_text:
                text_to_embed = f"User: {q.query_text}\nAssistant: {q.answer_text}"
                embedding = await embedder.embed_text(text_to_embed)
                point = qmodels.PointStruct(
                    id=query_id,
                    vector=embedding,
                    payload={
                        "session_id": session_id,
                        "text": text_to_embed,
                        "role": "exchange"
                    }
                )
                await qdrant_db.upsert_chat_memory([point])

            # 2. Ensure ChatSession exists
            session_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
            chat_session = session_result.scalar_one_or_none()
            if not chat_session:
                chat_session = ChatSession(
                    id=session_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    title=q.query_text[:50] if q else "New Session"
                )
                db.add(chat_session)
                await db.commit()

            # 3. Level 3: Long-term State Summarization
            count_result = await db.execute(select(func.count(Query.id)).where(Query.session_id == session_id))
            query_count = count_result.scalar()

            if query_count > 0 and query_count % 5 == 0:
                recent_q_result = await db.execute(
                    select(Query)
                    .where(Query.session_id == session_id)
                    .order_by(Query.created_at.desc())
                    .limit(5)
                )
                recent_queries = recent_q_result.scalars().all()
                recent_queries.reverse()

                exchanges = []
                for rq in recent_queries:
                    exchanges.append({"role": "user", "content": rq.query_text})
                    if rq.answer_text:
                        exchanges.append({"role": "assistant", "content": rq.answer_text})

                new_summary = await generator.summarize_session(chat_session.summary_state, exchanges)
                chat_session.summary_state = new_summary
                await db.commit()

    except Exception as e:
        logger.error(f"Background memory cleanup failed: {e}")
