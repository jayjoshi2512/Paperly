import tiktoken
from typing import List
from .base import BaseChunker

class FixedSizeChunker(BaseChunker):
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk(self, text: str) -> List[str]:
        tokens = self.encoding.encode(text)
        chunks = []
        
        if not tokens:
            return []
            
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunks.append(self.encoding.decode(chunk_tokens))
            start += (self.chunk_size - self.overlap)
            
        return chunks
