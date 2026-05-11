from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models import Chunk, Document

from app.auth.router import router as auth_router
from app.documents.router import router as docs_router
from app.rag.bm25_index import bm25_manager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 2: BM25 index rebuild from MySQL
    logger.info("Rebuilding BM25 index from MySQL...")
    async with AsyncSessionLocal() as session:
        # Fetch all chunks joined with document to get workspace_id
        result = await session.execute(
            select(Chunk.id, Chunk.chunk_text, Document.workspace_id)
            .join(Document, Chunk.document_id == Document.id)
        )
        
        # Group by workspace_id
        workspace_corpora = {}
        for chunk_id, text, ws_id in result:
            if ws_id not in workspace_corpora:
                workspace_corpora[ws_id] = []
            workspace_corpora[ws_id].append((chunk_id, text))
            
        for ws_id, corpus in workspace_corpora.items():
            bm25_manager.build(ws_id, corpus)
            
    logger.info("BM25 index rebuilt successfully.")
    yield
    # Cleanup logic if any

app = FastAPI(
    title="Paperly API",
    description="Enterprise Document Intelligence Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(docs_router)

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "ok"}
