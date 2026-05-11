from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum, JSON, text
from sqlalchemy.orm import relationship
from app.database import Base

class RoleEnum(str, enum.Enum):
    admin = "admin"
    member = "member"

class DocStatusEnum(str, enum.Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"

class ChunkingStrategyEnum(str, enum.Enum):
    fixed = "fixed"
    recursive = "recursive"
    semantic = "semantic"

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, server_default=text("(UUID())"))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    users = relationship("User", back_populates="workspace", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="workspace", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, server_default=text("(UUID())"))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.member)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    workspace = relationship("Workspace", back_populates="users")
    uploaded_documents = relationship("Document", back_populates="uploader")
    queries = relationship("Query", back_populates="user")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, server_default=text("(UUID())"))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer)
    page_count = Column(Integer)
    chunking_strategy = Column(Enum(ChunkingStrategyEnum), nullable=False, default=ChunkingStrategyEnum.recursive)
    chunk_count = Column(Integer)
    status = Column(Enum(DocStatusEnum), nullable=False, default=DocStatusEnum.processing)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    workspace = relationship("Workspace", back_populates="documents")
    uploader = relationship("User", back_populates="uploaded_documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, server_default=text("(UUID())"))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    qdrant_point_id = Column(String(36), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer)
    token_count = Column(Integer)
    chunk_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    document = relationship("Document", back_populates="chunks")

class Query(Base):
    __tablename__ = "queries"

    id = Column(String(36), primary_key=True, server_default=text("(UUID())"))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text)
    retrieved_chunk_ids = Column(JSON)
    was_answered = Column(Boolean, nullable=False, default=True)
    faithfulness_score = Column(Float)
    relevancy_score = Column(Float)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    workspace = relationship("Workspace", back_populates="queries")
    user = relationship("User", back_populates="queries")

class UnansweredQuery(Base):
    __tablename__ = "unanswered_queries"

    id = Column(String(36), primary_key=True, server_default=text("(UUID())"))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    cluster_label = Column(String(255))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

class DocumentDiff(Base):
    __tablename__ = "document_diffs"

    id = Column(String(36), primary_key=True, server_default=text("(UUID())"))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    from_version = Column(Integer, nullable=False)
    to_version = Column(Integer, nullable=False)
    diff_summary = Column(JSON)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
