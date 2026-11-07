import re
from typing import Dict, Any, List

# Authoritative domain tiers
TIER_1_STANDARDS = ["rfc-editor.org", "ietf.org", "w3.org", "iso.org", "acm.org", "ieee.org"]
TIER_2_DOCUMENTATION = [
    "developer.mozilla.org", "postgresql.org", "docs.oracle.com", "python.org",
    "docs.microsoft.com", "learn.microsoft.com", "kernel.org", "curl.se", "apache.org"
]
TIER_3_EDUCATIONAL = [
    ".edu", "wikipedia.org", "geeksforgeeks.org", "baeldung.com",
    "digitalocean.com", "martinfowler.com", "freecodecamp.org"
]

def evaluate_and_rank_source(
    url: str,
    title: str,
    full_text: str,
    learning_objective: str
) -> Dict[str, Any]:
    """
    Evaluates source credibility, publisher tier, and objective alignment
    using transparent heuristic criteria. Returns score and justification notes.
    """
    url_lower = url.lower()
    text_lower = full_text.lower()
    obj_lower = learning_objective.lower()

    # 1. Authority Scoring
    base_authority = 0.65
    authority_tier = "Tier 4 - General Web Source"

    if any(d in url_lower for d in TIER_1_STANDARDS):
        base_authority = 0.98
        authority_tier = "Tier 1 - Primary Standard / IETF Specification"
    elif any(d in url_lower for d in TIER_2_DOCUMENTATION):
        base_authority = 0.92
        authority_tier = "Tier 2 - Authoritative Official Developer Documentation"
    elif any(d in url_lower for d in TIER_3_EDUCATIONAL):
        base_authority = 0.82
        authority_tier = "Tier 3 - Established Educational / Academic Publication"

    # 2. Objective Concept Coverage
    # Extract salient terms from objective (words with length >= 3)
    key_terms = [w for w in re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', obj_lower) if w not in {"explain", "distinguish", "between", "and", "the", "for", "with"}]
    matched_terms = [t for t in key_terms if t in text_lower or t in title.lower()]
    coverage_ratio = len(matched_terms) / max(len(key_terms), 1)

    # 3. Content Completeness & Depth
    content_length = len(full_text)
    # Generously weight length without overly penalizing concise authoritative specifications
    depth_score = min(content_length / 2000.0, 1.0)

    # Compute Final Score (weighted combination)
    raw_score = (base_authority * 0.60) + (coverage_ratio * 0.30) + (depth_score * 0.10)
    final_score = round(min(max(raw_score, 0.20), 0.99), 2)

    notes = {
        "authority_tier": authority_tier,
        "base_authority": base_authority,
        "matched_concepts": matched_terms,
        "concept_coverage_percent": int(coverage_ratio * 100),
        "text_character_count": content_length,
        "evaluation_summary": (
            f"Classified as {authority_tier}. Matched {len(matched_terms)}/{len(key_terms)} key objective concepts "
            f"({', '.join(matched_terms[:6]) or 'None'}). Content depth: {content_length} characters."
        )
    }

    return {
        "relevance_score": final_score,
        "evaluation_notes": notes
    }
