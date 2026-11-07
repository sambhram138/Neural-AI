import re
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_pdf_pages(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text page-by-page from an instructor-uploaded PDF file.
    Retains page numbers for claim-level citation mapping.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file '{file_path}' does not exist.")

    pages_data = []
    try:
        import pymupdf
        doc = pymupdf.open(file_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text").strip()
            if text:
                pages_data.append({
                    "page_number": page_idx + 1,
                    "text": text,
                    "character_count": len(text)
                })
        doc.close()
    except ImportError:
        logger.warning("PyMuPDF is not installed; reading as fallback text if available.")
    except Exception as e:
        logger.error(f"Error extracting PDF with PyMuPDF: {e}")
        raise

    return pages_data

def chunk_pdf_pages(pages_data: List[Dict[str, Any]], chunk_size: int = 600) -> List[Dict[str, Any]]:
    """
    Splits page texts into structured chunks while strictly preserving page numbers.
    """
    chunks = []
    for page in pages_data:
        p_num = page["page_number"]
        paragraphs = [p.strip() for p in page["text"].split("\n\n") if len(p.strip()) > 30]
        
        current_chunk = []
        current_len = 0
        for p in paragraphs:
            if current_len + len(p) > chunk_size and current_chunk:
                chunks.append({
                    "chunk_text": "\n".join(current_chunk),
                    "page_number": p_num,
                    "section_heading": f"Page {p_num} Section"
                })
                current_chunk = [p]
                current_len = len(p)
            else:
                current_chunk.append(p)
                current_len += len(p)
                
        if current_chunk:
            chunks.append({
                "chunk_text": "\n".join(current_chunk),
                "page_number": p_num,
                "section_heading": f"Page {p_num} Section"
            })

    return chunks

def retrieve_relevant_book_chunks(
    chunks: List[Dict[str, Any]],
    title: str,
    learning_objective: str,
    top_k: int = 6
) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant passages from the book chunks matching the lesson objective.
    Uses term frequency and conceptual keyword density.
    """
    search_terms = set(re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', (title + " " + learning_objective).lower()))
    
    scored_chunks = []
    for chunk in chunks:
        text_lower = chunk["chunk_text"].lower()
        score = sum(text_lower.count(term) for term in search_terms)
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in scored_chunks[:top_k]]
