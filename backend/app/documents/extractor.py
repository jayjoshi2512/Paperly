from dataclasses import dataclass
from typing import List
import fitz  # PyMuPDF
import io

@dataclass
class PageText:
    page_number: int
    text: str
    char_count: int

class ExtractionError(Exception):
    pass

def extract_text_from_pdf(file_bytes: bytes) -> List[PageText]:
    """
    Extracts text from PDF bytes.
    Strips headers and footers heuristically (top/bottom 5% of the page).
    """
    if not file_bytes:
        return []
        
    # Check magic number for PDF
    if not file_bytes.startswith(b'%PDF'):
        raise ExtractionError("Invalid file type: Not a PDF")
        
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        # Corrupt PDF
        return []
        
    pages = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Get dimensions
        rect = page.rect
        page_height = rect.height
        
        top_margin = page_height * 0.05
        bottom_margin = page_height * 0.95
        
        # Extract blocks: (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks")
        
        content_blocks = []
        for b in blocks:
            # Check if block is text (block_type == 0)
            if b[6] == 0:
                y0 = b[1]
                y1 = b[3]
                
                # Check if block is outside top/bottom 5%
                if y0 >= top_margin and y1 <= bottom_margin:
                    content_blocks.append(b[4].strip())
                    
        page_text = "\n".join(content_blocks).strip()
        if page_text:
            pages.append(PageText(
                page_number=page_num + 1,
                text=page_text,
                char_count=len(page_text)
            ))
            
    doc.close()
    return pages
