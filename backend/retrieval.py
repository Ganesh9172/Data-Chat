import math
import re
import numpy as np
from typing import List, Dict, Any, Optional

from backend.database import (
    get_all_chunks_with_embeddings,
    get_all_qa_with_embeddings,
    get_active_knowledge_updates
)
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
    Retrieves:
    1. Active approved Knowledge Updates (prioritized as authoritative overrides).
    2. Most relevant chunks from the 6 source PDFs.
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

    # 1. Retrieve & Score Active Approved Knowledge Updates (Two-Way Communicative System)
    active_updates = get_active_knowledge_updates()
    relevant_updates = []
    
    # Stop words to prevent matching on 'what', 'is', 'the', etc.
    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
        "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
        "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", 
        "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", 
        "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "me", "more", 
        "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", 
        "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", 
        "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then", 
        "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", 
        "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", 
        "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
    }

    q_content_tokens = {t for t in tokenize(q_clean) if t not in STOP_WORDS and len(t) > 1}

    if active_updates and q_content_tokens:
        for u in active_updates:
            sim = 0.0
            if u.get("embedding"):
                try:
                    u_emb = bytes_to_vector(u["embedding"])
                    if u_emb.shape == q_unit.shape:
                        u_norm = np.linalg.norm(u_emb)
                        unit_u_emb = u_emb / u_norm if u_norm > 0 else u_emb
                        sim = float(np.dot(unit_u_emb, q_unit))
                except Exception:
                    sim = 0.0

            # Content token match (excluding stop words) across original and corrected text
            combined_text = f"{u['original_information']} {u['corrected_information']} {u.get('reason') or ''}"
            u_content_tokens = {t for t in tokenize(combined_text) if t not in STOP_WORDS and len(t) > 1}
            shared_content = q_content_tokens.intersection(u_content_tokens)
            
            # An update is relevant ONLY if:
            # 1. Very strong semantic match (sim >= 0.72), OR
            # 2. Strong semantic match (sim >= 0.65) AND at least one shared non-stopword technical token, OR
            # 3. Moderate semantic match (sim >= 0.58) AND at least two shared non-stopword technical tokens
            is_relevant = (sim >= 0.72) or (sim >= 0.65 and len(shared_content) >= 1) or (sim >= 0.58 and len(shared_content) >= 2)
            
            if is_relevant:
                update_num = u.get("update_number") or 1
                source_doc = u.get("source_document") or "01_Hydronic_Water_Pressure_Field_Guide.pdf"
                source_page = u.get("source_page") or 1
                
                content_str = (
                    f"APPROVED KNOWLEDGE BASE UPDATE #{update_num} (Authoritative Field Override):\n"
                    f"Corrected Information: {u['corrected_information']}\n"
                    f"Supersedes / Corrects: {u['original_information']}\n"
                    f"Original Reference: {source_doc}, Page {source_page}\n"
                    f"Reason / Notes: {u.get('reason') or 'Approved field update by authorized user'}"
                )
                
                relevant_updates.append({
                    "document_name": f"Knowledge Base Update #{update_num}",
                    "page_number": source_page,
                    "original_source": f"{source_doc}, Page {source_page}",
                    "source_document": source_doc,
                    "update_number": update_num,
                    "snippet": u["corrected_information"][:240],
                    "content": content_str,
                    "similarity": round(sim, 4),
                    "type": "knowledge_update",
                    "original_information": u["original_information"],
                    "corrected_information": u["corrected_information"]
                })

        relevant_updates.sort(key=lambda x: x["similarity"], reverse=True)

    # 2. Retrieve PDF Chunks
    chunks = get_all_chunks_with_embeddings()
    if not chunks:
        return relevant_updates[:top_k]

    # Prepare vectors and token sets for PDF chunks
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
        return relevant_updates[:top_k]

    # Dense Semantic Cosine Similarities
    emb_matrix = np.vstack(emb_list) # (N, D)
    dense_sims = np.dot(emb_matrix, q_unit) # (N,)

    # BM25 / Lexical Scoring for exact terminology
    q_tokens_list = tokenize(q_clean)
    N = len(valid_chunks)
    avgdl = sum(len(t) for t in chunk_tokens_list) / max(1, N)
    
    # Calculate IDF for query tokens
    idf = {}
    for qt in set(q_tokens_list):
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
        for qt in q_tokens_list:
            if qt not in idf or idf[qt] <= 0:
                continue
            tf = dt.count(qt)
            if tf > 0:
                score += idf[qt] * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / avgdl)))
        bm25_scores.append(score)

    max_bm25 = max(bm25_scores) if bm25_scores and max(bm25_scores) > 0 else 1.0
    norm_bm25 = [s / max_bm25 for s in bm25_scores]

    # Compute Hybrid Score (65% Semantic + 35% Lexical)
    hybrid_matches = []
    for idx, chunk in enumerate(valid_chunks):
        d_sim = float(dense_sims[idx])
        b_sim = float(norm_bm25[idx])
        combined = 0.65 * d_sim + 0.35 * b_sim
        
        doc_name = chunk["document_name"]
        snippet = chunk["content"][:240] + ("..." if len(chunk["content"]) > 240 else "")
        page_num = chunk.get("page_number")
        page_start = chunk.get("page_start", page_num)
        page_end = chunk.get("page_end", page_num)
        hybrid_matches.append({
            "document_name": doc_name,
            "page_number": page_num if page_num is not None else 1,
            "page_start": page_start,
            "page_end": page_end,
            "snippet": snippet,
            "content": chunk["content"],
            "similarity": round(combined, 4),
            "dense_score": round(d_sim, 4),
            "lexical_score": round(b_sim, 4),
            "type": "document"
        })

    hybrid_matches.sort(key=lambda x: x["similarity"], reverse=True)

    # Dynamic Relevance Thresholding for PDF chunks
    filtered = []
    if hybrid_matches:
        top_score = hybrid_matches[0]["similarity"]
        min_cutoff = max(similarity_threshold, top_score * 0.75)
        
        seen_docs = {}
        for item in hybrid_matches:
            if item["similarity"] < min_cutoff:
                continue
            dname = item["document_name"]
            doc_count = seen_docs.get(dname, 0)
            if doc_count < 3:
                filtered.append(item)
                seen_docs[dname] = doc_count + 1
            if len(filtered) >= top_k:
                break

        if not filtered and top_score >= 0.40:
            filtered = [hybrid_matches[0]]

    # Prioritize Approved Knowledge Updates at the top of context
    combined_results = relevant_updates + filtered
    return combined_results[:max(top_k, len(relevant_updates) + 2)]
