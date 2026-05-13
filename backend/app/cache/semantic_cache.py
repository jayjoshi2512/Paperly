"""Semantic query cache — cosine-similarity lookup against recent answered queries.

Architecture:
- Per-workspace LRU of (embedding, answer, query_id) tuples (max 200 entries).
- On each new query, embed it and compute cosine similarity against all cached entries.
- If max similarity >= SIMILARITY_THRESHOLD, return the cached answer (cache hit).
- Cache is in-process memory only — cleared on restart. This is intentional: stale
  answers after document re-uploads would be wrong. The 30-minute TTL prevents serving
  outdated answers after a document set changes significantly.
"""
from __future__ import annotations

import time
import math
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92   # cosine similarity cutoff
MAX_CACHE_SIZE       = 200    # per-workspace max entries
TTL_SECONDS          = 1800   # 30 minutes


@dataclass
class _CacheEntry:
    embedding: List[float]
    answer:    str
    query_id:  str
    ts:        float = field(default_factory=time.time)


def _cosine(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot  = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticCache:
    """Thread-safe (single-process) per-workspace semantic cache."""

    def __init__(self) -> None:
        # workspace_id -> deque of _CacheEntry
        self._store: Dict[str, Deque[_CacheEntry]] = {}

    def _get_store(self, workspace_id: str) -> Deque[_CacheEntry]:
        if workspace_id not in self._store:
            self._store[workspace_id] = deque(maxlen=MAX_CACHE_SIZE)
        return self._store[workspace_id]

    def lookup(
        self, workspace_id: str, embedding: List[float]
    ) -> Optional[Tuple[str, str, float]]:
        """
        Return (answer, query_id, similarity) if a cache hit exists, else None.
        Expired entries are skipped (but not immediately evicted for speed).
        """
        now = time.time()
        store = self._get_store(workspace_id)
        best_sim = 0.0
        best_entry: Optional[_CacheEntry] = None

        for entry in store:
            if now - entry.ts > TTL_SECONDS:
                continue
            sim = _cosine(embedding, entry.embedding)
            if sim > best_sim:
                best_sim = sim
                best_entry = entry

        if best_entry and best_sim >= SIMILARITY_THRESHOLD:
            logger.info(
                f"Semantic cache HIT (workspace={workspace_id[:8]}, "
                f"sim={best_sim:.3f}, query_id={best_entry.query_id})"
            )
            return best_entry.answer, best_entry.query_id, best_sim

        return None

    def store(
        self,
        workspace_id: str,
        embedding: List[float],
        answer: str,
        query_id: str,
    ) -> None:
        """Add a new entry to the cache."""
        entry = _CacheEntry(embedding=embedding, answer=answer, query_id=query_id)
        self._get_store(workspace_id).append(entry)

    def invalidate_workspace(self, workspace_id: str) -> None:
        """Clear all cache entries for a workspace (e.g., on document delete/re-upload)."""
        if workspace_id in self._store:
            self._store[workspace_id].clear()
            logger.info(f"Semantic cache invalidated for workspace={workspace_id[:8]}")


# Singleton — shared across all requests within the process
semantic_cache = SemanticCache()
