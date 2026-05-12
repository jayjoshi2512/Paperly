from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback

from app.database import AsyncSessionLocal, engine
from sqlalchemy import select
from app.models import Chunk, Document

from app.auth.router import router as auth_router
from app.documents.router import router as docs_router
from app.chat.router import router as chat_router
from app.eval.router import router as eval_router
from app.admin.router import router as admin_router
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
    # Shutdown: dispose engine to properly close all pooled connections
    logger.info("Disposing database engine...")
    await engine.dispose()
    logger.info("Shutdown complete.")

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
app.include_router(chat_router)
app.include_router(eval_router)
app.include_router(admin_router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler that ensures CORS headers are always present."""
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "ok"}
