import re
from typing import List, Tuple, Dict
from rank_bm25 import BM25Okapi

class WorkspaceIndex:
    def __init__(self):
        self.chunk_ids: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: BM25Okapi | None = None

    def rebuild(self):
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

class BM25Manager:
    """
    In-memory BM25 sparse search index.
    In Paperly, there's one BM25 index per workspace. 
    """
    def __init__(self):
        self.workspaces: Dict[str, WorkspaceIndex] = {}

    def _tokenize(self, text: str) -> List[str]:
        """Lowercase + split on whitespace/punctuation."""
        return [word.lower() for word in re.split(r'\W+', text) if word]

    def build(self, workspace_id: str, corpus: List[Tuple[str, str]]):
        """Build index from scratch for a workspace. corpus is (chunk_id, text) pairs"""
        idx = WorkspaceIndex()
        for cid, text in corpus:
            idx.chunk_ids.append(cid)
            idx.tokenized_corpus.append(self._tokenize(text))
        idx.rebuild()
        self.workspaces[workspace_id] = idx

    def get_scores(self, workspace_id: str, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """Returns list of (chunk_id, score) for a query in a workspace."""
        if workspace_id not in self.workspaces:
            return []
            
        idx = self.workspaces[workspace_id]
        if idx.bm25 is None:
            return []
            
        tokenized_query = self._tokenize(query)
        scores = idx.bm25.get_scores(tokenized_query)
        
        scored_chunks = list(zip(idx.chunk_ids, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    def add_document(self, workspace_id: str, chunks: List[Tuple[str, str]]):
        """Incremental update: add chunks and rebuild index."""
        if workspace_id not in self.workspaces:
            self.workspaces[workspace_id] = WorkspaceIndex()
            
        idx = self.workspaces[workspace_id]
        for cid, text in chunks:
            idx.chunk_ids.append(cid)
            idx.tokenized_corpus.append(self._tokenize(text))
        idx.rebuild()

    def remove_document(self, workspace_id: str, chunk_ids_to_remove: List[str]):
        """Remove chunks for deleted doc and rebuild index."""
        if workspace_id not in self.workspaces:
            return
            
        idx = self.workspaces[workspace_id]
        to_remove = set(chunk_ids_to_remove)
        
        new_ids = []
        new_corpus = []
        for cid, tokens in zip(idx.chunk_ids, idx.tokenized_corpus):
            if cid not in to_remove:
                new_ids.append(cid)
                new_corpus.append(tokens)
                
        idx.chunk_ids = new_ids
        idx.tokenized_corpus = new_corpus
        idx.rebuild()

# Singleton
bm25_manager = BM25Manager()
