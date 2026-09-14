import sqlite3
import json
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "firebird.db")

def get_db_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        chunk_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Chunks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        document_name TEXT NOT NULL,
        page_number INTEGER,
        content TEXT NOT NULL,
        embedding BLOB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    """)

    # Q&A pairs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qa_pairs (
        id TEXT PRIMARY KEY,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        source TEXT NOT NULL,
        embedding BLOB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Conversations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        sources TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

# --- Document Operations ---
def insert_document(doc_id: str, name: str, file_type: str, file_size: int = 0) -> str:
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO documents (id, name, file_type, file_size, chunk_count) VALUES (?, ?, ?, ?, 0)",
        (doc_id, name, file_type, file_size)
    )
    conn.commit()
    conn.close()
    return doc_id

def insert_chunks(chunks_data: List[Dict[str, Any]]):
    conn = get_db_connection()
    cursor = conn.cursor()
    doc_chunk_counts: Dict[str, int] = {}
    
    for item in chunks_data:
        chunk_id = item.get("id", str(uuid.uuid4()))
        doc_id = item["document_id"]
        doc_name = item["document_name"]
        page_num = item.get("page_number")
        content = item["content"]
        embedding_blob = item["embedding"] # bytes
        
        cursor.execute(
            """
            INSERT INTO chunks (id, document_id, document_name, page_number, content, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chunk_id, doc_id, doc_name, page_num, content, embedding_blob)
        )
        doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1

    for doc_id, count in doc_chunk_counts.items():
        cursor.execute(
            "UPDATE documents SET chunk_count = chunk_count + ? WHERE id = ?",
            (count, doc_id)
        )

    conn.commit()
    conn.close()

def get_all_documents() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_document(doc_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_all_chunks_with_embeddings() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT id, document_id, document_name, page_number, content, embedding FROM chunks").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Q&A Operations ---
def insert_qa_pair(qa_id: str, question: str, answer: str, source: str, embedding_bytes: bytes) -> str:
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO qa_pairs (id, question, answer, source, embedding) VALUES (?, ?, ?, ?, ?)",
        (qa_id, question, answer, source, embedding_bytes)
    )
    conn.commit()
    conn.close()
    return qa_id

def get_all_qa_pairs() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT id, question, answer, source, created_at FROM qa_pairs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_qa_with_embeddings() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT id, question, answer, source, embedding FROM qa_pairs").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_qa_pair(qa_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM qa_pairs WHERE id = ?", (qa_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# --- Conversation & Message Operations ---
def create_conversation(title: str = "New Conversation") -> str:
    conv_id = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute("INSERT INTO conversations (id, title) VALUES (?, ?)", (conv_id, title))
    conn.commit()
    conn.close()
    return conv_id

def get_all_conversations() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_conversation(conv_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not row:
        conn.close()
        return None
    conv = dict(row)
    msg_rows = conn.execute(
        "SELECT id, role, content, sources, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conv_id,)
    ).fetchall()
    conn.close()
    conv["messages"] = []
    for m in msg_rows:
        m_dict = dict(m)
        if m_dict["sources"]:
            try:
                m_dict["sources"] = json.loads(m_dict["sources"])
            except Exception:
                pass
        conv["messages"].append(m_dict)
    return conv

def update_conversation_title(conv_id: str, title: str):
    conn = get_db_connection()
    conn.execute(
        "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, conv_id)
    )
    conn.commit()
    conn.close()

def delete_conversation(conv_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def insert_message(conv_id: str, role: str, content: str, sources: Optional[List[Dict[str, Any]]] = None) -> str:
    msg_id = str(uuid.uuid4())
    sources_json = json.dumps(sources) if sources else None
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO messages (id, conversation_id, role, content, sources) VALUES (?, ?, ?, ?, ?)",
        (msg_id, conv_id, role, content, sources_json)
    )
    conn.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()
    return msg_id

def get_stats() -> Dict[str, int]:
    conn = get_db_connection()
    doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    qa_count = conn.execute("SELECT COUNT(*) FROM qa_pairs").fetchone()[0]
    conv_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    conn.close()
    return {
        "documents": doc_count,
        "chunks": chunk_count,
        "qa_pairs": qa_count,
        "conversations": conv_count
    }
