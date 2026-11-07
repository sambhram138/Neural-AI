import re
from typing import List

def generate_research_queries(title: str, learning_objective: str) -> List[str]:
    """
    Generates targeted, concept-specific search queries using the lesson title
    and learning objective. Avoids superficial searches of the title alone.
    """
    queries = []
    
    # 1. Broad technical scope query
    clean_title = re.sub(r'[^\w\s-]', '', title).strip()
    queries.append(f"{clean_title} official documentation overview")
    
    # 2. Extract concepts from learning objective
    obj_lower = learning_objective.lower()
    
    if "get" in obj_lower and "post" in obj_lower:
        queries.append("HTTP request methods GET vs POST RFC 9110 safe idempotent semantics")
    if "status" in obj_lower or "2xx" in obj_lower or "4xx" in obj_lower or "5xx" in obj_lower:
        queries.append("HTTP response status code categories 2xx 4xx 5xx specifications")
        queries.append("HTTP client error 4xx vs server error 5xx troubleshooting")
        
    if "1nf" in obj_lower or "2nf" in obj_lower or "3nf" in obj_lower or "normalization" in obj_lower:
        queries.append("Database normalization 1NF 2NF 3NF functional dependencies rules")
        queries.append("Relational database design update insertion deletion anomalies examples")
        queries.append("First second third normal forms worked table decomposition")
        
    # 3. Add practical / worked example query
    queries.append(f"{clean_title} worked examples practical applications")
    
    # Deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        q_norm = q.strip().lower()
        if q_norm not in seen:
            seen.add(q_norm)
            unique_queries.append(q)
            
    return unique_queries[:5]
