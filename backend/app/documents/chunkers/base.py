from abc import ABC, abstractmethod
from typing import List

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """Split text into chunks."""
        pass
