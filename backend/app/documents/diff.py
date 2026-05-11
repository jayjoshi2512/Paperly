from dataclasses import dataclass
from typing import List
import difflib

@dataclass
class DiffResult:
    added: List[str]
    removed: List[str]
    modified: List[str]
    unchanged_count: int

def compute_chunk_diff(old_chunks: List[str], new_chunks: List[str]) -> DiffResult:
    """
    Compares two lists of chunk texts.
    Returns added, removed, modified, and unchanged counts.
    """
    matcher = difflib.SequenceMatcher(None, old_chunks, new_chunks)
    
    added = []
    removed = []
    modified = []
    unchanged_count = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            unchanged_count += (i2 - i1)
        elif tag == 'insert':
            added.extend(new_chunks[j1:j2])
        elif tag == 'delete':
            removed.extend(old_chunks[i1:i2])
        elif tag == 'replace':
            # Simplified replace: consider all items in replace range as modified
            modified.extend(new_chunks[j1:j2])
            
    return DiffResult(
        added=added,
        removed=removed,
        modified=modified,
        unchanged_count=unchanged_count
    )
