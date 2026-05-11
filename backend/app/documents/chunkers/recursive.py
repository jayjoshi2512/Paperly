from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .base import BaseChunker

class RecursiveChunker(BaseChunker):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk(self, text: str) -> List[str]:
        if not text.strip():
            return []
        return self.splitter.split_text(text)
