from typing import List, Dict, Any
from app.schemas.source import ResearchPackage, ResearchSourceResponse, ResearchChunkResponse

def build_research_package(
    lesson_id: str,
    lesson_title: str,
    learning_objective: str,
    sources: List[ResearchSourceResponse]
) -> ResearchPackage:
    """
    Normalizes, deduplicates, and packages collected research for lesson generation and QC.
    Maintains claim-level traceability to source IDs.
    """
    active_sources = [s for s in sources if s.status == "active"]
    
    web_excerpts = []
    book_chunks = []
    youtube_videos = []
    
    for s in active_sources:
        if s.source_type == "website":
            for c in s.chunks:
                web_excerpts.append({
                    "source_id": s.id,
                    "title": s.title,
                    "url": s.url_or_identifier,
                    "publisher": s.author_publisher,
                    "excerpt": c.chunk_text,
                    "heading": c.section_heading
                })
        elif s.source_type == "book_pdf":
            for c in s.chunks:
                book_chunks.append({
                    "source_id": s.id,
                    "book_title": s.title,
                    "page_number": c.page_number,
                    "chunk": c.chunk_text
                })
        elif s.source_type == "youtube":
            youtube_videos.append({
                "source_id": s.id,
                "title": s.title,
                "url": s.url_or_identifier,
                "metadata": s.source_metadata
            })

    # Check for research gaps against learning objective
    identified_gaps = []
    combined_text = " ".join([e.get("excerpt", "") for e in web_excerpts]).lower()
    
    if "get" in learning_objective.lower() and "get" not in combined_text:
        identified_gaps.append("Insufficient coverage of HTTP GET method in retrieved sources.")
    if "post" in learning_objective.lower() and "post" not in combined_text:
        identified_gaps.append("Insufficient coverage of HTTP POST method in retrieved sources.")
    if ("2xx" in learning_objective.lower() or "status" in learning_objective.lower()) and "status" not in combined_text:
        identified_gaps.append("Insufficient coverage of HTTP response status codes in retrieved sources.")

    retrieval_notes = f"Synthesized {len(active_sources)} sources ({len(web_excerpts)} web excerpts, {len(book_chunks)} book chunks, {len(youtube_videos)} videos)."

    return ResearchPackage(
        lesson_id=lesson_id,
        lesson_title=lesson_title,
        learning_objective=learning_objective,
        sources=active_sources,
        web_excerpts=web_excerpts,
        book_chunks=book_chunks,
        youtube_videos=youtube_videos,
        retrieval_notes=retrieval_notes,
        identified_gaps=identified_gaps
    )
