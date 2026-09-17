import os
import uuid
import re
import glob
from typing import List, Dict, Any, Optional
from pypdf import PdfReader

from backend.database import (
    insert_document,
    insert_chunks,
    insert_qa_pair,
    delete_document,
    delete_qa_pair,
    get_all_documents,
    get_all_qa_pairs,
    clear_official_knowledge
)
from backend.embeddings import (
    get_embedding,
    get_embeddings_batch,
    vector_to_bytes
)

KNOWLEDGE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "knowledge")
os.makedirs(KNOWLEDGE_DATA_DIR, exist_ok=True)

def clean_text(text: str) -> str:
    """Normalizes excessive newlines and whitespace."""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def chunk_pdf_page(page_text: str, doc_name: str, max_chunk_chars: int = 1200) -> List[str]:
    """
    Splits PDF page text into clean semantic chunks along section headers (e.g. '1. ', '2. ')
    and paragraph boundaries. Never splits in the middle of words or table rows.
    Also appends a unified page chunk if the page is compact (<= 2600 chars).
    """
    cleaned = clean_text(page_text)
    if not cleaned:
        return []
        
    # Split on numbered sections (e.g., '\n1. ', '\n2. ', '\n3. ')
    section_splits = re.split(r'(?=\n[0-9]+\.\s+[A-Z])', cleaned)
    chunks = []
    
    for part in section_splits:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_chunk_chars:
            chunks.append(part)
        else:
            # Sub-split by double newlines without breaking sentences
            paragraphs = re.split(r'\n{2,}', part)
            curr = ""
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                if len(curr) + len(p) + 2 <= max_chunk_chars:
                    curr = (curr + "\n\n" + p).strip()
                else:
                    if curr:
                        chunks.append(curr)
                    curr = p
            if curr:
                chunks.append(curr)
                
    # Add a unified full-page chunk for compact pages so cross-section relationships
    # (e.g., measurements table + work notes) remain seamlessly retrievable
    if len(cleaned) <= 2600 and len(chunks) > 1:
        chunks.append(cleaned)
        
    return chunks

def chunk_text(text: str, chunk_size: int = 900, chunk_overlap: int = 150) -> List[str]:
    """
    General paragraph-aware text chunker for plain text files.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]
        
    paragraphs = re.split(r'\n{2,}', cleaned)
    chunks = []
    curr = ""
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(curr) + len(p) + 2 <= chunk_size:
            curr = (curr + "\n\n" + p).strip()
        else:
            if curr:
                chunks.append(curr)
            if len(p) > chunk_size:
                # Break long paragraph on sentence boundaries
                sentences = re.split(r'(?<=[.!?])\s+', p)
                sub_curr = ""
                for s in sentences:
                    if len(sub_curr) + len(s) + 1 <= chunk_size:
                        sub_curr = (sub_curr + " " + s).strip()
                    else:
                        if sub_curr:
                            chunks.append(sub_curr)
                        sub_curr = s
                if sub_curr:
                    curr = sub_curr
            else:
                curr = p
    if curr:
        chunks.append(curr)
    return chunks

def process_pdf_file(file_path: str, original_filename: str) -> Dict[str, Any]:
    """
    Extracts text page-by-page from PDF, creates semantic chunks preserving page numbers,
    generates dense local embeddings, and stores in SQLite.
    """
    doc_id = str(uuid.uuid4())
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    insert_document(doc_id, original_filename, "pdf", file_size, page_count=total_pages)
    
    chunks_to_embed = []
    
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_text = page.extract_text() or ""
        text_chunks = chunk_pdf_page(page_text, original_filename)
        for chunk in text_chunks:
            chunks_to_embed.append({
                "page_number": page_num,
                "page_start": page_num,
                "page_end": page_num,
                "content": chunk
            })
            
    if not chunks_to_embed:
        return {"document_id": doc_id, "document_name": original_filename, "chunk_count": 0, "pages": total_pages}
        
    # Generate embeddings via FastEmbed
    texts = [item["content"] for item in chunks_to_embed]
    embeddings = get_embeddings_batch(texts)
    
    chunk_records = []
    for item, emb in zip(chunks_to_embed, embeddings):
        chunk_records.append({
            "id": str(uuid.uuid4()),
            "document_id": doc_id,
            "document_name": original_filename,
            "page_number": item["page_number"],
            "page_start": item.get("page_start", item["page_number"]),
            "page_end": item.get("page_end", item["page_number"]),
            "content": item["content"],
            "embedding": vector_to_bytes(emb)
        })
        
    insert_chunks(chunk_records)
    return {
        "document_id": doc_id,
        "document_name": original_filename,
        "chunk_count": len(chunk_records),
        "pages": total_pages
    }

def process_text_content(content: str, filename: str, file_type: str = "text") -> Dict[str, Any]:
    """
    Processes plain text or Markdown content, generates chunks and embeddings, and indexes into SQLite.
    """
    doc_id = str(uuid.uuid4())
    insert_document(doc_id, filename, file_type, len(content.encode("utf-8")))
    
    text_chunks = chunk_text(content)
    chunks_to_embed = [{"page_number": 1, "content": c} for c in text_chunks]
            
    if not chunks_to_embed:
        return {"document_id": doc_id, "document_name": filename, "chunk_count": 0}
        
    texts = [item["content"] for item in chunks_to_embed]
    embeddings = get_embeddings_batch(texts)
    
    chunk_records = []
    for item, emb in zip(chunks_to_embed, embeddings):
        chunk_records.append({
            "id": str(uuid.uuid4()),
            "document_id": doc_id,
            "document_name": filename,
            "page_number": item["page_number"],
            "content": item["content"],
            "embedding": vector_to_bytes(emb)
        })
        
    insert_chunks(chunk_records)
    return {
        "document_id": doc_id,
        "document_name": filename,
        "chunk_count": len(chunk_records)
    }

def process_qa_entry(question: str, answer: str, source: str = "User Approved Q&A") -> Dict[str, Any]:
    """
    Stores an approved Q&A pair and indexes its embedding into SQLite.
    """
    qa_id = str(uuid.uuid4())
    combined_text = f"Question: {question}\nAnswer: {answer}\nSource: {source}"
    emb = get_embedding(f"{question} {answer}")
    emb_bytes = vector_to_bytes(emb)
    
    insert_qa_pair(qa_id, question, answer, source, emb_bytes)
    
    qa_doc_name = f"Approved Q&A: {question[:30]}..."
    qa_doc_id = str(uuid.uuid4())
    insert_document(qa_doc_id, qa_doc_name, "qa", len(combined_text.encode("utf-8")))
    insert_chunks([{
        "id": str(uuid.uuid4()),
        "document_id": qa_doc_id,
        "document_name": source or "Approved Q&A",
        "page_number": None,
        "content": combined_text,
        "embedding": emb_bytes
    }])
    
    return {
        "qa_id": qa_id,
        "question": question,
        "answer": answer,
        "source": source
    }

def sync_official_knowledge_base():
    """
    Synchronizes the database with the 6 official source-of-truth PDFs in data/knowledge.
    Cleans up duplicate documents, obsolete chunks, and unverified QA entries.
    """
    clear_official_knowledge()
    
    pdf_pattern = os.path.join(KNOWLEDGE_DATA_DIR, "0*.pdf")
    pdf_files = sorted(glob.glob(pdf_pattern))
    
    results = []
    for pdf_path in pdf_files:
        fname = os.path.basename(pdf_path)
        res = process_pdf_file(pdf_path, fname)
        results.append(res)
        print(f"[Knowledge Sync] Indexed {fname}: {res['chunk_count']} chunks")
        
    return results
