import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Ensure root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from backend.database import (
    init_db,
    get_db_session,
    get_stats,
    Document,
    Chunk,
    QAPair,
    Conversation,
    Message
)

SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "firebird.db")

def parse_sqlite_dt(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(val_str)
    except Exception:
        return None

def migrate():
    print("=" * 70)
    print("FIREBIRD AI — SQLITE TO MICROSOFT SQL SERVER MIGRATION")
    print("=" * 70)
    
    if not os.path.exists(SQLITE_PATH):
        print(f"[!] SQLite database not found at '{SQLITE_PATH}'. Nothing to migrate.")
        return

    print(f"Source SQLite Database: {SQLITE_PATH}")
    db_url = os.getenv("DATABASE_URL", "")
    print(f"Target SQL Server URL: {db_url}")

    # 1. Initialize SQL Server Schema
    print("\n[Step 1/5] Ensuring SQL Server tables exist...")
    init_db()

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    session = get_db_session()
    try:
        # 2. Migrate Documents
        print("\n[Step 2/5] Migrating 'documents' table...")
        sqlite_cur.execute("SELECT * FROM documents")
        sqlite_docs = sqlite_cur.fetchall()
        print(f"Found {len(sqlite_docs)} document(s) in SQLite.")
        
        doc_count = 0
        for row in sqlite_docs:
            existing = session.query(Document).filter_by(id=row["id"]).first()
            if not existing:
                doc = Document(
                    id=row["id"],
                    name=row["name"],
                    file_type=row["file_type"],
                    file_size=row["file_size"] or 0,
                    chunk_count=row["chunk_count"] or 0,
                    created_at=parse_sqlite_dt(row["created_at"])
                )
                session.add(doc)
                doc_count += 1
        session.commit()
        print(f"Migrated {doc_count} new document record(s) to SQL Server.")

        # 3. Migrate Chunks
        print("\n[Step 3/5] Migrating 'chunks' table...")
        sqlite_cur.execute("SELECT * FROM chunks")
        sqlite_chunks = sqlite_cur.fetchall()
        print(f"Found {len(sqlite_chunks)} chunk(s) in SQLite.")
        
        chunk_count = 0
        for row in sqlite_chunks:
            existing = session.query(Chunk).filter_by(id=row["id"]).first()
            if not existing:
                emb = row["embedding"]
                if isinstance(emb, memoryview):
                    emb = emb.tobytes()
                chunk = Chunk(
                    id=row["id"],
                    document_id=row["document_id"],
                    document_name=row["document_name"],
                    page_number=row["page_number"],
                    content=row["content"],
                    embedding=emb,
                    created_at=parse_sqlite_dt(row["created_at"])
                )
                session.add(chunk)
                chunk_count += 1
        session.commit()
        print(f"Migrated {chunk_count} new chunk record(s) to SQL Server.")

        # 4. Migrate QA Pairs
        print("\n[Step 4/5] Migrating 'qa_pairs' table...")
        sqlite_cur.execute("SELECT * FROM qa_pairs")
        sqlite_qa = sqlite_cur.fetchall()
        print(f"Found {len(sqlite_qa)} Q&A pair(s) in SQLite.")
        
        qa_count = 0
        for row in sqlite_qa:
            existing = session.query(QAPair).filter_by(id=row["id"]).first()
            if not existing:
                emb = row["embedding"]
                if isinstance(emb, memoryview):
                    emb = emb.tobytes()
                qa = QAPair(
                    id=row["id"],
                    question=row["question"],
                    answer=row["answer"],
                    source=row["source"],
                    embedding=emb,
                    created_at=parse_sqlite_dt(row["created_at"])
                )
                session.add(qa)
                qa_count += 1
        session.commit()
        print(f"Migrated {qa_count} new Q&A record(s) to SQL Server.")

        # 5. Migrate Conversations & Messages
        print("\n[Step 5/5] Migrating 'conversations' and 'messages' tables...")
        sqlite_cur.execute("SELECT * FROM conversations")
        sqlite_convs = sqlite_cur.fetchall()
        print(f"Found {len(sqlite_convs)} conversation(s) in SQLite.")
        
        conv_count = 0
        for row in sqlite_convs:
            existing = session.query(Conversation).filter_by(id=row["id"]).first()
            if not existing:
                conv = Conversation(
                    id=row["id"],
                    title=row["title"],
                    created_at=parse_sqlite_dt(row["created_at"]),
                    updated_at=parse_sqlite_dt(row["updated_at"])
                )
                session.add(conv)
                conv_count += 1
        session.commit()
        print(f"Migrated {conv_count} new conversation record(s) to SQL Server.")

        sqlite_cur.execute("SELECT * FROM messages")
        sqlite_msgs = sqlite_cur.fetchall()
        print(f"Found {len(sqlite_msgs)} message(s) in SQLite.")
        
        msg_count = 0
        for row in sqlite_msgs:
            existing = session.query(Message).filter_by(id=row["id"]).first()
            if not existing:
                msg = Message(
                    id=row["id"],
                    conversation_id=row["conversation_id"],
                    role=row["role"],
                    content=row["content"],
                    sources=row["sources"],
                    created_at=parse_sqlite_dt(row["created_at"])
                )
                session.add(msg)
                msg_count += 1
        session.commit()
        print(f"Migrated {msg_count} new message record(s) to SQL Server.")

        # Verification: Compare Counts
        print("\n" + "=" * 70)
        print("VERIFICATION OF MIGRATION COUNTS")
        print("=" * 70)
        
        counts = {
            "documents": (len(sqlite_docs), session.query(Document).count()),
            "chunks": (len(sqlite_chunks), session.query(Chunk).count()),
            "qa_pairs": (len(sqlite_qa), session.query(QAPair).count()),
            "conversations": (len(sqlite_convs), session.query(Conversation).count()),
            "messages": (len(sqlite_msgs), session.query(Message).count())
        }

        all_match = True
        for tbl, (src_cnt, dst_cnt) in counts.items():
            match_status = "MATCH [OK]" if src_cnt == dst_cnt else "MISMATCH [!]"
            if src_cnt != dst_cnt:
                all_match = False
            print(f"  Table '{tbl:15}': SQLite={src_cnt:4} | SQL Server={dst_cnt:4} | {match_status}")

        if all_match:
            print("\n>> SUCCESS: All tables and records migrated and verified successfully!")
        else:
            print("\n>> WARNING: Some record counts did not match exactly.")

        print(f">> Original SQLite database preserved at '{SQLITE_PATH}'.")

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise e
    finally:
        session.close()
        sqlite_conn.close()

if __name__ == "__main__":
    migrate()
