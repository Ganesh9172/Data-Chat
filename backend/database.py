import os
import json
import uuid
import base64
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime

# Path Configuration for JSON Data Storage
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

DOCUMENTS_FILE = os.path.join(DATA_DIR, "documents.json")
CHAT_HISTORY_FILE = os.path.join(DATA_DIR, "chat_history.json")
KNOWLEDGE_UPDATES_FILE = os.path.join(DATA_DIR, "knowledge_updates.json")
QA_HISTORY_FILE = os.path.join(DATA_DIR, "qa_history.json")
CHUNKS_FILE = os.path.join(DATA_DIR, "chunks.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PERMISSIONS_FILE = os.path.join(DATA_DIR, "permissions.json")

_lock = threading.RLock()


import time

# --- Atomic File Read / Write Utilities ---

def _read_json_file(filepath: str) -> List[Dict[str, Any]]:
    if not os.path.exists(filepath):
        return []
    max_retries = 6
    for attempt in range(max_retries):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (PermissionError, json.JSONDecodeError, OSError):
            if attempt == max_retries - 1:
                return []
            time.sleep(0.02 * (attempt + 1))
        except Exception as e:
            print(f"[JSON Storage] Error reading {filepath}: {e}")
            return []
    return []

def _write_json_file(filepath: str, data: List[Dict[str, Any]]):
    tmp_path = filepath + f".tmp_{uuid.uuid4().hex}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Windows retry loop to handle momentary locks from concurrent reads
        max_retries = 8
        for attempt in range(max_retries):
            try:
                os.replace(tmp_path, filepath)
                break
            except (PermissionError, OSError) as pe:
                if attempt == max_retries - 1:
                    raise pe
                time.sleep(0.05 * (attempt + 1))
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise RuntimeError(f"Failed to write JSON file '{filepath}': {e}") from e

def _encode_embedding(emb: Any) -> Optional[str]:
    if emb is None:
        return None
    if isinstance(emb, bytes):
        return base64.b64encode(emb).decode("ascii")
    if isinstance(emb, str):
        return emb
    return None

def _decode_embedding(emb_str: Any) -> Optional[bytes]:
    if not emb_str:
        return None
    if isinstance(emb_str, bytes):
        return emb_str
    if isinstance(emb_str, str):
        try:
            return base64.b64decode(emb_str.encode("ascii"))
        except Exception:
            return None
    return None


# --- Initialization & Automatic One-Time Migration ---

def _migrate_from_sqlite_if_needed():
    """
    If the JSON files are empty but data/firebird.db exists,
    perform a seamless one-time migration to populate the JSON storage.
    """
    sqlite_path = os.path.join(DATA_DIR, "firebird.db")
    if not os.path.exists(sqlite_path):
        return

    docs = _read_json_file(DOCUMENTS_FILE)
    if docs:
        # Already populated
        return

    try:
        import sqlite3
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Check if SQLite has documents
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not cur.fetchone():
            conn.close()
            return

        # 1. Documents
        cur.execute("SELECT * FROM documents")
        migrated_docs = []
        for r in cur.fetchall():
            migrated_docs.append({
                "id": r["id"],
                "name": r["name"],
                "filename": r["name"],
                "file_type": r["file_type"],
                "file_size": r["file_size"] or 0,
                "chunk_count": r["chunk_count"] or 0,
                "page_count": 1,
                "status": "indexed",
                "upload_date": str(r["created_at"]) if r["created_at"] else datetime.utcnow().isoformat(),
                "created_at": str(r["created_at"]) if r["created_at"] else datetime.utcnow().isoformat()
            })
        _write_json_file(DOCUMENTS_FILE, migrated_docs)

        # 2. Chunks
        cur.execute("SELECT * FROM chunks")
        migrated_chunks = []
        for r in cur.fetchall():
            emb = r["embedding"]
            if isinstance(emb, memoryview):
                emb = emb.tobytes()
            migrated_chunks.append({
                "id": r["id"],
                "document_id": r["document_id"],
                "document_name": r["document_name"],
                "page_number": r["page_number"],
                "content": r["content"],
                "embedding": _encode_embedding(emb),
                "created_at": str(r["created_at"]) if r["created_at"] else datetime.utcnow().isoformat()
            })
        _write_json_file(CHUNKS_FILE, migrated_chunks)

        # 3. QA Pairs
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qa_pairs'")
        if cur.fetchone():
            cur.execute("SELECT * FROM qa_pairs")
            migrated_qa = []
            for r in cur.fetchall():
                emb = r["embedding"]
                if isinstance(emb, memoryview):
                    emb = emb.tobytes()
                migrated_qa.append({
                    "id": r["id"],
                    "question": r["question"],
                    "answer": r["answer"],
                    "source": r["source"],
                    "embedding": _encode_embedding(emb),
                    "created_at": str(r["created_at"]) if r["created_at"] else datetime.utcnow().isoformat()
                })
            _write_json_file(QA_HISTORY_FILE, migrated_qa)

        # 4. Conversations & Messages
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
        if cur.fetchone():
            cur.execute("SELECT * FROM conversations")
            raw_convs = cur.fetchall()
            cur.execute("SELECT * FROM messages ORDER BY created_at ASC")
            raw_msgs = cur.fetchall()

            msgs_by_conv: Dict[str, List[Dict[str, Any]]] = {}
            for m in raw_msgs:
                cid = m["conversation_id"]
                if cid not in msgs_by_conv:
                    msgs_by_conv[cid] = []
                sources = m["sources"]
                if isinstance(sources, str) and sources.strip():
                    try:
                        sources = json.loads(sources)
                    except Exception:
                        pass
                msgs_by_conv[cid].append({
                    "id": m["id"],
                    "conversation_id": cid,
                    "role": m["role"],
                    "content": m["content"],
                    "sources": sources,
                    "created_at": str(m["created_at"]) if m["created_at"] else datetime.utcnow().isoformat()
                })

            migrated_convs = []
            for c in raw_convs:
                cid = c["id"]
                migrated_convs.append({
                    "id": cid,
                    "title": c["title"],
                    "created_at": str(c["created_at"]) if c["created_at"] else datetime.utcnow().isoformat(),
                    "updated_at": str(c["updated_at"]) if c["updated_at"] else datetime.utcnow().isoformat(),
                    "messages": msgs_by_conv.get(cid, [])
                })
            _write_json_file(CHAT_HISTORY_FILE, migrated_convs)

        conn.close()
        print(f"[JSON Storage] Successfully migrated initial data from {sqlite_path}: {len(migrated_docs)} documents, {len(migrated_chunks)} chunks.")
    except Exception as e:
        print(f"[JSON Storage] Migration from SQLite skipped or failed: {e}")

# --- User & Permission Management (RBAC) ---

DEFAULT_USER_PERMISSIONS = {
    "view_own_chats": True,
    "create_chat": True,
    "edit_own_chat": True,
    "delete_own_chat": True,
    "upload_documents": False,
    "delete_documents": False,
    "update_knowledge": False,
    "manage_users": False,
    "view_all_chats": False
}

ADMIN_PERMISSIONS = {
    "view_own_chats": True,
    "create_chat": True,
    "edit_own_chat": True,
    "delete_own_chat": True,
    "upload_documents": True,
    "delete_documents": True,
    "update_knowledge": True,
    "manage_users": True,
    "view_all_chats": True
}

def get_user_permissions(user_id: str, role: str = "USER") -> Dict[str, bool]:
    if role == "ADMIN":
        return dict(ADMIN_PERMISSIONS)
    
    perms = dict(DEFAULT_USER_PERMISSIONS)
    with _lock:
        all_perms = _read_json_file(PERMISSIONS_FILE)
        for p in all_perms:
            if p.get("user_id") == user_id:
                for k, v in p.items():
                    if k != "user_id" and isinstance(v, bool):
                        perms[k] = v
                break
    return perms

def update_user_permissions(user_id: str, new_perms: Dict[str, bool]) -> Dict[str, bool]:
    with _lock:
        all_perms = _read_json_file(PERMISSIONS_FILE)
        found = False
        for p in all_perms:
            if p.get("user_id") == user_id:
                for k, v in new_perms.items():
                    if k != "user_id" and isinstance(v, bool):
                        p[k] = v
                found = True
                break
        if not found:
            entry = {"user_id": user_id}
            for k, v in new_perms.items():
                if k != "user_id" and isinstance(v, bool):
                    entry[k] = v
            all_perms.append(entry)
        _write_json_file(PERMISSIONS_FILE, all_perms)

    user = get_user_by_id(user_id)
    role = user.get("role", "USER") if user else "USER"
    return get_user_permissions(user_id, role)

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        users = _read_json_file(USERS_FILE)
        for u in users:
            if u.get("id") == user_id:
                return dict(u)
        return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    if not email:
        return None
    email_clean = email.lower().strip()
    with _lock:
        users = _read_json_file(USERS_FILE)
        for u in users:
            if u.get("email", "").lower().strip() == email_clean:
                return dict(u)
        return None

def get_all_users() -> List[Dict[str, Any]]:
    with _lock:
        users = _read_json_file(USERS_FILE)
        result = []
        for u in users:
            item = dict(u)
            item.pop("password_hash", None)
            item["permissions"] = get_user_permissions(u["id"], u.get("role", "USER"))
            result.append(item)
        return result

def create_user(email: str, password: str, name: str, role: str = "USER") -> Dict[str, Any]:
    from backend.auth import hash_password
    with _lock:
        existing = get_user_by_email(email)
        if existing:
            raise ValueError(f"User with email '{email}' already exists")
        
        users = _read_json_file(USERS_FILE)
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        new_user = {
            "id": user_id,
            "email": email.lower().strip(),
            "name": name.strip(),
            "role": role.upper(),
            "active": True,
            "password_hash": hash_password(password),
            "created_at": datetime.utcnow().isoformat()
        }
        users.append(new_user)
        _write_json_file(USERS_FILE, users)

        out = dict(new_user)
        out.pop("password_hash", None)
        out["permissions"] = get_user_permissions(user_id, role.upper())
        return out

def _init_users_and_permissions():
    from backend.auth import hash_password
    with _lock:
        users = _read_json_file(USERS_FILE)
        permissions = _read_json_file(PERMISSIONS_FILE)
        
        # 1. Admin account initialization
        admin_exists = any(u.get("role") == "ADMIN" for u in users)
        admin_id = "user-admin-001"
        if not admin_exists:
            admin_email = os.getenv("ADMIN_EMAIL", "admin@firebird.internal").strip().lower()
            admin_pass = os.getenv("ADMIN_PASSWORD", "AdminSecurePass123!").strip()
            users.append({
                "id": admin_id,
                "email": admin_email,
                "name": "System Administrator",
                "role": "ADMIN",
                "active": True,
                "password_hash": hash_password(admin_pass),
                "created_at": datetime.utcnow().isoformat()
            })
            print(f"[JSON Storage] Seeded initial ADMIN user: {admin_email}")
        else:
            for u in users:
                if u.get("role") == "ADMIN":
                    admin_id = u.get("id", admin_id)
                    break

        # 2. Seed required test accounts if not already present
        existing_emails = {u.get("email", "").lower() for u in users}
        if "usera@firebird.internal" not in existing_emails:
            users.append({
                "id": "user-a-001",
                "email": "usera@firebird.internal",
                "name": "User A",
                "role": "USER",
                "active": True,
                "password_hash": hash_password("UserA123!"),
                "created_at": datetime.utcnow().isoformat()
            })
        if "userb@firebird.internal" not in existing_emails:
            users.append({
                "id": "user-b-002",
                "email": "userb@firebird.internal",
                "name": "User B",
                "role": "USER",
                "active": True,
                "password_hash": hash_password("UserB123!"),
                "created_at": datetime.utcnow().isoformat()
            })
        if "ganesh@firebird.internal" not in existing_emails:
            users.append({
                "id": "user-ganesh-003",
                "email": "ganesh@firebird.internal",
                "name": "Ganesh",
                "role": "USER",
                "active": True,
                "password_hash": hash_password("Ganesh123!"),
                "created_at": datetime.utcnow().isoformat()
            })

        _write_json_file(USERS_FILE, users)

        # 3. Ensure Ganesh has specific permission overrides in permissions.json
        ganesh_perm_exists = any(p.get("user_id") == "user-ganesh-003" for p in permissions)
        if not ganesh_perm_exists:
            permissions.append({
                "user_id": "user-ganesh-003",
                "upload_documents": True,
                "delete_documents": False,
                "update_knowledge": True
            })
            _write_json_file(PERMISSIONS_FILE, permissions)

        # 4. Migrate any legacy conversations without user_id to admin
        convs = _read_json_file(CHAT_HISTORY_FILE)
        convs_updated = False
        for c in convs:
            if not c.get("user_id"):
                c["user_id"] = admin_id
                convs_updated = True
            for m in c.get("messages", []):
                if not m.get("user_id"):
                    m["user_id"] = c["user_id"]
                    convs_updated = True
        if convs_updated:
            _write_json_file(CHAT_HISTORY_FILE, convs)
            print("[JSON Storage] Migrated legacy conversations without user_id to admin.")

def init_db():
    """
    Initializes JSON file storage. Creates documents.json, chat_history.json,
    knowledge_updates.json, qa_history.json, chunks.json, users.json, and permissions.json
    if they do not exist.
    """
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        for filepath in [DOCUMENTS_FILE, CHAT_HISTORY_FILE, KNOWLEDGE_UPDATES_FILE, QA_HISTORY_FILE, CHUNKS_FILE, USERS_FILE, PERMISSIONS_FILE]:
            if not os.path.exists(filepath):
                _write_json_file(filepath, [])

        # Check for one-time migration if files are empty
        _migrate_from_sqlite_if_needed()
        _init_users_and_permissions()
        print("[JSON Storage] JSON file storage initialized successfully.")


# --- Document Operations ---

def insert_document(doc_id: str, name: str, file_type: str, file_size: int = 0, page_count: int = 1) -> str:
    with _lock:
        docs = _read_json_file(DOCUMENTS_FILE)
        now_str = datetime.utcnow().isoformat()
        found = False
        for doc in docs:
            if doc.get("id") == doc_id:
                doc["name"] = name
                doc["filename"] = name
                doc["file_type"] = file_type
                doc["file_size"] = file_size
                if page_count > 1 or not doc.get("page_count"):
                    doc["page_count"] = page_count
                found = True
                break
        if not found:
            docs.append({
                "id": doc_id,
                "name": name,
                "filename": name,
                "file_type": file_type,
                "file_size": file_size,
                "chunk_count": 0,
                "page_count": page_count,
                "status": "indexed",
                "upload_date": now_str,
                "created_at": now_str
            })
        _write_json_file(DOCUMENTS_FILE, docs)
        return doc_id

def insert_chunks(chunks_data: List[Dict[str, Any]]):
    with _lock:
        chunks = _read_json_file(CHUNKS_FILE)
        docs = _read_json_file(DOCUMENTS_FILE)
        doc_chunk_counts: Dict[str, int] = {}
        now_str = datetime.utcnow().isoformat()

        for item in chunks_data:
            chunk_id = item.get("id") or str(uuid.uuid4())
            doc_id = item["document_id"]
            doc_name = item["document_name"]
            page_num = item.get("page_number")
            page_start = item.get("page_start", page_num)
            page_end = item.get("page_end", page_num)
            content = item["content"]
            emb = item.get("embedding")
            emb_str = _encode_embedding(emb)

            chunks.append({
                "id": chunk_id,
                "document_id": doc_id,
                "document_name": doc_name,
                "page_number": page_num,
                "page_start": page_start,
                "page_end": page_end,
                "content": content,
                "embedding": emb_str,
                "created_at": item.get("created_at") or now_str
            })
            doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1

        for doc in docs:
            did = doc.get("id")
            if did in doc_chunk_counts:
                doc["chunk_count"] = (doc.get("chunk_count") or 0) + doc_chunk_counts[did]

        _write_json_file(CHUNKS_FILE, chunks)
        _write_json_file(DOCUMENTS_FILE, docs)

def get_all_documents() -> List[Dict[str, Any]]:
    with _lock:
        docs = _read_json_file(DOCUMENTS_FILE)
        docs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return docs

def delete_document(doc_id: str) -> bool:
    with _lock:
        docs = _read_json_file(DOCUMENTS_FILE)
        initial_len = len(docs)
        docs = [d for d in docs if d.get("id") != doc_id]
        if len(docs) == initial_len:
            return False

        _write_json_file(DOCUMENTS_FILE, docs)

        # Cascade delete chunks
        chunks = _read_json_file(CHUNKS_FILE)
        chunks = [c for c in chunks if c.get("document_id") != doc_id]
        _write_json_file(CHUNKS_FILE, chunks)
        return True

def get_all_chunks_with_embeddings() -> List[Dict[str, Any]]:
    with _lock:
        chunks = _read_json_file(CHUNKS_FILE)
        result = []
        for c in chunks:
            raw_emb = c.get("embedding")
            decoded_emb = _decode_embedding(raw_emb)
            result.append({
                "id": c["id"],
                "document_id": c["document_id"],
                "document_name": c["document_name"],
                "page_number": c.get("page_number"),
                "page_start": c.get("page_start", c.get("page_number")),
                "page_end": c.get("page_end", c.get("page_number")),
                "content": c["content"],
                "embedding": decoded_emb,
                "created_at": c.get("created_at")
            })
        return result

def clear_official_knowledge():
    """Clears documents, chunks, and QA pairs for re-indexing."""
    with _lock:
        _write_json_file(DOCUMENTS_FILE, [])
        _write_json_file(CHUNKS_FILE, [])
        _write_json_file(QA_HISTORY_FILE, [])


# --- Q&A Operations ---

def insert_qa_pair(qa_id: str, question: str, answer: str, source: str, embedding_bytes: bytes) -> str:
    with _lock:
        qa_pairs = _read_json_file(QA_HISTORY_FILE)
        now_str = datetime.utcnow().isoformat()
        qa_pairs.append({
            "id": qa_id,
            "question": question,
            "answer": answer,
            "source": source,
            "embedding": _encode_embedding(embedding_bytes),
            "created_at": now_str
        })
        _write_json_file(QA_HISTORY_FILE, qa_pairs)
        return qa_id

def get_all_qa_pairs() -> List[Dict[str, Any]]:
    with _lock:
        qa_pairs = _read_json_file(QA_HISTORY_FILE)
        qa_pairs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        res = []
        for q in qa_pairs:
            res.append({
                "id": q["id"],
                "question": q["question"],
                "answer": q["answer"],
                "source": q["source"],
                "created_at": q.get("created_at")
            })
        return res

def get_all_qa_with_embeddings() -> List[Dict[str, Any]]:
    with _lock:
        qa_pairs = _read_json_file(QA_HISTORY_FILE)
        res = []
        for q in qa_pairs:
            res.append({
                "id": q["id"],
                "question": q["question"],
                "answer": q["answer"],
                "source": q["source"],
                "embedding": _decode_embedding(q.get("embedding")),
                "created_at": q.get("created_at")
            })
        return res

def delete_qa_pair(qa_id: str) -> bool:
    with _lock:
        qa_pairs = _read_json_file(QA_HISTORY_FILE)
        initial_len = len(qa_pairs)
        qa_pairs = [q for q in qa_pairs if q.get("id") != qa_id]
        if len(qa_pairs) == initial_len:
            return False
        _write_json_file(QA_HISTORY_FILE, qa_pairs)
        return True


# --- Conversation & Message Operations ---

def create_conversation(title: str = "New Conversation", user_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
    with _lock:
        conv_id = str(uuid.uuid4())
        convs = _read_json_file(CHAT_HISTORY_FILE)
        now_str = datetime.utcnow().isoformat()
        owner_id = session_id or user_id
        convs.append({
            "id": conv_id,
            "user_id": owner_id,
            "session_id": owner_id,
            "title": title,
            "created_at": now_str,
            "updated_at": now_str,
            "messages": []
        })
        _write_json_file(CHAT_HISTORY_FILE, convs)
        return conv_id

def get_all_conversations(user_id: Optional[str] = None, session_id: Optional[str] = None, is_admin: bool = False, view_all: bool = False) -> List[Dict[str, Any]]:
    with _lock:
        convs = _read_json_file(CHAT_HISTORY_FILE)
        owner_id = session_id or user_id
        if not (is_admin or view_all):
            if owner_id:
                convs = [c for c in convs if c.get("session_id") == owner_id or c.get("user_id") == owner_id]
            else:
                convs = []
        convs.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
        return [{
            "id": c["id"],
            "user_id": c.get("user_id") or c.get("session_id"),
            "session_id": c.get("session_id") or c.get("user_id"),
            "title": c["title"],
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at")
        } for c in convs]

def get_conversation(conv_id: str, user_id: Optional[str] = None, session_id: Optional[str] = None, is_admin: bool = False, view_all: bool = False) -> Optional[Dict[str, Any]]:
    with _lock:
        convs = _read_json_file(CHAT_HISTORY_FILE)
        owner_id = session_id or user_id
        for c in convs:
            if c.get("id") == conv_id:
                if owner_id is not None and not (is_admin or view_all):
                    c_owner = c.get("session_id") or c.get("user_id")
                    if c_owner != owner_id:
                        return None
                return {
                    "id": c["id"],
                    "user_id": c.get("user_id") or c.get("session_id"),
                    "session_id": c.get("session_id") or c.get("user_id"),
                    "title": c["title"],
                    "created_at": c.get("created_at"),
                    "updated_at": c.get("updated_at"),
                    "messages": c.get("messages", [])
                }
        return None

def update_conversation_title(conv_id: str, title: str, user_id: Optional[str] = None, session_id: Optional[str] = None, is_admin: bool = False) -> bool:
    with _lock:
        convs = _read_json_file(CHAT_HISTORY_FILE)
        owner_id = session_id or user_id
        for c in convs:
            if c.get("id") == conv_id:
                if not is_admin:
                    c_owner = c.get("session_id") or c.get("user_id")
                    if not owner_id or c_owner != owner_id:
                        return False
                c["title"] = title
                c["updated_at"] = datetime.utcnow().isoformat()
                _write_json_file(CHAT_HISTORY_FILE, convs)
                return True
        return False

def delete_conversation(conv_id: str, user_id: Optional[str] = None, session_id: Optional[str] = None, is_admin: bool = False) -> bool:
    with _lock:
        convs = _read_json_file(CHAT_HISTORY_FILE)
        owner_id = session_id or user_id
        target = None
        for c in convs:
            if c.get("id") == conv_id:
                target = c
                break
        if not target:
            return False
        if not is_admin:
            c_owner = target.get("session_id") or target.get("user_id")
            if not owner_id or c_owner != owner_id:
                return False
        convs = [c for c in convs if c.get("id") != conv_id]
        _write_json_file(CHAT_HISTORY_FILE, convs)
        return True

def insert_message(
    conv_id: str,
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None,
    user_id: Optional[str] = None,
    related_video: Optional[Dict[str, Any]] = None
) -> str:
    with _lock:
        msg_id = str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat()
        convs = _read_json_file(CHAT_HISTORY_FILE)
        
        msg_record = {
            "id": msg_id,
            "conversation_id": conv_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "sources": sources,
            "created_at": now_str
        }
        if related_video:
            msg_record["related_video"] = related_video

        found = False
        for c in convs:
            if c.get("id") == conv_id:
                if user_id and not c.get("user_id"):
                    c["user_id"] = user_id
                if "messages" not in c or not isinstance(c["messages"], list):
                    c["messages"] = []
                msg_record["user_id"] = user_id or c.get("user_id")
                c["messages"].append(msg_record)
                c["updated_at"] = now_str
                found = True
                break
                
        if not found:
            convs.append({
                "id": conv_id,
                "user_id": user_id,
                "title": content[:40].strip() or "New Conversation",
                "created_at": now_str,
                "updated_at": now_str,
                "messages": [msg_record]
            })
            
        _write_json_file(CHAT_HISTORY_FILE, convs)
        return msg_id


# --- Two-Way Communicative Knowledge Updates Operations ---

def get_next_update_number() -> int:
    updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
    max_num = 0
    for u in updates:
        num = u.get("update_number")
        if isinstance(num, int) and num > max_num:
            max_num = num
    return max_num + 1

def create_knowledge_update(
    original_information: str,
    corrected_information: str,
    source_document: Optional[str] = None,
    source_page: Optional[int] = None,
    reason: Optional[str] = None,
    status: str = "pending",
    created_by: str = "authorized_user",
    conversation_id: Optional[str] = None,
    embedding: Optional[bytes] = None
) -> Dict[str, Any]:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        update_id = str(uuid.uuid4())
        update_num = get_next_update_number()
        is_active = (status == "approved")
        now_str = datetime.utcnow().isoformat()
        approved_at = now_str if is_active else None

        record = {
            "id": update_id,
            "update_number": update_num,
            "conversation_id": conversation_id,
            "original_information": original_information,
            "corrected_information": corrected_information,
            "source_document": source_document,
            "source_page": source_page,
            "reason": reason,
            "status": status,
            "created_by": created_by,
            "created_at": now_str,
            "approved_at": approved_at,
            "version": 1,
            "active": is_active,
            "embedding": _encode_embedding(embedding)
        }
        updates.append(record)
        _write_json_file(KNOWLEDGE_UPDATES_FILE, updates)

        out = dict(record)
        out.pop("embedding", None)
        return out

def approve_knowledge_update(update_id: str, embedding: Optional[bytes] = None) -> bool:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        found = False
        now_str = datetime.utcnow().isoformat()
        for u in updates:
            if u.get("id") == update_id:
                u["status"] = "approved"
                u["active"] = True
                u["approved_at"] = now_str
                if embedding is not None:
                    u["embedding"] = _encode_embedding(embedding)
                found = True
                break
        if found:
            _write_json_file(KNOWLEDGE_UPDATES_FILE, updates)
            return True
        return False

def reject_knowledge_update(update_id: str) -> bool:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        found = False
        for u in updates:
            if u.get("id") == update_id:
                u["status"] = "rejected"
                u["active"] = False
                found = True
                break
        if found:
            _write_json_file(KNOWLEDGE_UPDATES_FILE, updates)
            return True
        return False

def revert_knowledge_update(update_id: str) -> bool:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        found = False
        for u in updates:
            if u.get("id") == update_id:
                u["status"] = "reverted"
                u["active"] = False
                found = True
                break
        if found:
            _write_json_file(KNOWLEDGE_UPDATES_FILE, updates)
            return True
        return False

def delete_knowledge_update(update_id: str) -> bool:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        initial_len = len(updates)
        updates = [u for u in updates if u.get("id") != update_id]
        if len(updates) == initial_len:
            return False
        _write_json_file(KNOWLEDGE_UPDATES_FILE, updates)
        return True

def get_all_knowledge_updates() -> List[Dict[str, Any]]:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        updates.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        res = []
        for u in updates:
            item = dict(u)
            item.pop("embedding", None)
            res.append(item)
        return res

def get_active_knowledge_updates() -> List[Dict[str, Any]]:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        res = []
        for u in updates:
            if u.get("status") == "approved" and u.get("active") is True:
                item = dict(u)
                item["embedding"] = _decode_embedding(item.get("embedding"))
                res.append(item)
        return res

def get_knowledge_update_by_id(update_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        for u in updates:
            if u.get("id") == update_id:
                item = dict(u)
                item["embedding"] = _decode_embedding(item.get("embedding"))
                return item
        return None

def get_pending_update_for_conversation(conv_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)
        matching = [u for u in updates if u.get("conversation_id") == conv_id and u.get("status") == "pending"]
        if not matching:
            return None
        matching.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        item = dict(matching[0])
        item.pop("embedding", None)
        return item


# --- Overall Stats ---

def get_stats() -> Dict[str, int]:
    with _lock:
        docs = _read_json_file(DOCUMENTS_FILE)
        chunks = _read_json_file(CHUNKS_FILE)
        qa = _read_json_file(QA_HISTORY_FILE)
        convs = _read_json_file(CHAT_HISTORY_FILE)
        updates = _read_json_file(KNOWLEDGE_UPDATES_FILE)

        ku_count = sum(1 for u in updates if u.get("status") == "approved" and u.get("active") is True)
        return {
            "documents": len(docs),
            "chunks": len(chunks),
            "qa_pairs": len(qa),
            "conversations": len(convs),
            "knowledge_updates": ku_count
        }
