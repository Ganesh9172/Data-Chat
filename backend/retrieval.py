import math
import re
import numpy as np
from typing import List, Dict, Any, Optional

from backend.database import get_all_chunks_with_embeddings, get_all_qa_with_embeddings
from backend.embeddings import get_embedding, bytes_to_vector

def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase alphanumeric and numeric tokens."""
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())

def retrieve_relevant_knowledge(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.45
) -> List[Dict[str, Any]]:
    """
    High-precision hybrid retrieval (Dense Semantic Vectors + BM25 Lexical Matching).
    Retrieves the most relevant chunks from the 6 source PDFs.
    Ensures multi-document retrieval when multiple PDFs contain relevant information,
    while strictly avoiding returning unrelated PDF content.
    """
    if not query or not query.strip():
        return []

    q_clean = query.strip()
    q_vec = get_embedding(q_clean)
    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0:
        return []
    q_unit = q_vec / q_norm

    chunks = get_all_chunks_with_embeddings()
    if not chunks:
        return []

    # 1. Prepare vectors and token sets
    valid_chunks = []
    emb_list = []
    chunk_tokens_list = []
    
    for c in chunks:
        try:
            emb = bytes_to_vector(c["embedding"])
            if emb.shape == q_unit.shape:
                norm = np.linalg.norm(emb)
                unit_emb = emb / norm if norm > 0 else emb
                emb_list.append(unit_emb)
                valid_chunks.append(c)
                chunk_tokens_list.append(tokenize(c["content"]))
        except Exception:
            continue

    if not valid_chunks:
        return []

    # 2. Dense Semantic Cosine Similarities
    emb_matrix = np.vstack(emb_list) # (N, D)
    dense_sims = np.dot(emb_matrix, q_unit) # (N,)

    # 3. BM25 / Lexical Scoring for exact terminology (e.g. F32, 0.7 bar, Delta-T, 70 C)
    q_tokens = tokenize(q_clean)
    N = len(valid_chunks)
    avgdl = sum(len(t) for t in chunk_tokens_list) / max(1, N)
    
    # Calculate IDF for query tokens
    idf = {}
    for qt in set(q_tokens):
        doc_freq = sum(1 for dt in chunk_tokens_list if qt in dt)
        if doc_freq > 0:
            idf[qt] = math.log(1 + (N - doc_freq + 0.5) / (doc_freq + 0.5))
        else:
            idf[qt] = 0.0

    bm25_scores = []
    k1 = 1.5
    b = 0.75
    for dt in chunk_tokens_list:
        dl = len(dt)
        score = 0.0
        for qt in q_tokens:
            if qt not in idf or idf[qt] <= 0:
                continue
            tf = dt.count(qt)
            if tf > 0:
                score += idf[qt] * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / avgdl)))
        bm25_scores.append(score)

    max_bm25 = max(bm25_scores) if bm25_scores and max(bm25_scores) > 0 else 1.0
    norm_bm25 = [s / max_bm25 for s in bm25_scores]

    # 4. Compute Hybrid Score (65% Semantic + 35% Lexical)
    hybrid_matches = []
    for idx, chunk in enumerate(valid_chunks):
        d_sim = float(dense_sims[idx])
        b_sim = float(norm_bm25[idx])
        combined = 0.65 * d_sim + 0.35 * b_sim
        
        doc_name = chunk["document_name"]
        snippet = chunk["content"][:240] + ("..." if len(chunk["content"]) > 240 else "")
        hybrid_matches.append({
            "document_name": doc_name,
            "page_number": chunk.get("page_number") or 1,
            "snippet": snippet,
            "content": chunk["content"],
            "similarity": round(combined, 4),
            "dense_score": round(d_sim, 4),
            "lexical_score": round(b_sim, 4),
            "type": "document"
        })

    # Sort descending by hybrid similarity
    hybrid_matches.sort(key=lambda x: x["similarity"], reverse=True)

    if not hybrid_matches:
        return []

    top_score = hybrid_matches[0]["similarity"]
    
    # 5. Dynamic Relevance Thresholding:
    # If the top score is very weak, no relevant documents exist for this query.
    # If top score is strong, only include chunks that are sufficiently close to top score
    # (prevents polluting context with unrelated documents from forced diversity).
    min_cutoff = max(similarity_threshold, top_score * 0.75)
    
    filtered = []
    seen_docs = {}
    
    for item in hybrid_matches:
        if item["similarity"] < min_cutoff:
            continue
        dname = item["document_name"]
        doc_count = seen_docs.get(dname, 0)
        # Allow up to 2 chunks per relevant document to ensure multi-document coverage
        if doc_count < 2:
            filtered.append(item)
            seen_docs[dname] = doc_count + 1
        if len(filtered) >= top_k:
            break

    # If nothing passed the cutoff, return at most the single top match if >= 0.40
    if not filtered and top_score >= 0.40:
        filtered = [hybrid_matches[0]]

    return filtered
