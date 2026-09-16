import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Text,
    LargeBinary,
    DateTime,
    Boolean,
    ForeignKey,
    func,
    select,
    desc,
    text
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError, DatabaseError

# Load environment
DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if "DATABASE_URL" not in os.environ:
    load_dotenv(DOTENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    DATABASE_URL = "mssql+pyodbc://@localhost/firebird_db?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes"

Base = declarative_base()

# --- SQLAlchemy ORM Models for Microsoft SQL Server ---

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document_name = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=True)
    content = Column(Text, nullable=False) # Maps to NVARCHAR(MAX) in SQL Server
    embedding = Column(LargeBinary, nullable=False) # Maps to VARBINARY(MAX) in SQL Server
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "content": self.content,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class QAPair(Base):
    __tablename__ = "qa_pairs"
    
    id = Column(String(36), primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source = Column(String(255), nullable=False)
    embedding = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if include_embedding:
            data["embedding"] = self.embedding
        return data


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True) # JSON string
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self) -> Dict[str, Any]:
        parsed_sources = None
        if self.sources:
            try:
                parsed_sources = json.loads(self.sources)
            except Exception:
                parsed_sources = None
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "sources": parsed_sources,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class KnowledgeUpdate(Base):
    __tablename__ = "knowledge_updates"
    
    id = Column(String(36), primary_key=True)
    update_number = Column(Integer, nullable=True)
    conversation_id = Column(String(36), nullable=True)
    original_information = Column(Text, nullable=False)
    corrected_information = Column(Text, nullable=False)
    source_document = Column(String(255), nullable=True)
    source_page = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending") # 'pending', 'approved', 'rejected', 'reverted'
    created_by = Column(String(100), nullable=False, default="authorized_user")
    created_at = Column(DateTime, server_default=func.now())
    approved_at = Column(DateTime, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True)
    embedding = Column(LargeBinary, nullable=True)

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "update_number": self.update_number,
            "conversation_id": self.conversation_id,
            "original_information": self.original_information,
            "corrected_information": self.corrected_information,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "reason": self.reason,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "version": self.version,
            "active": self.active
        }
        if include_embedding:
            data["embedding"] = self.embedding
        return data


# --- Engine & Session Management ---

_engine = None
_SessionFactory = None

def get_engine():
    global _engine, _SessionFactory
    if _engine is None:
        db_url = os.getenv("DATABASE_URL", "").strip()
        if not db_url:
            load_dotenv(DOTENV_PATH, override=True)
            db_url = os.getenv("DATABASE_URL", "").strip()
        if not db_url:
            db_url = "mssql+pyodbc://@localhost/firebird_db?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes"
        
        try:
            _engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                fast_executemany=True
            )
            # Test immediate connectivity
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
        except Exception as e:
            _engine = None
            _SessionFactory = None
            raise RuntimeError(
                f"DATABASE CONNECTION ERROR: Failed to connect to Microsoft SQL Server.\n"
                f"Connection URL: {db_url}\n"
                f"Details: {str(e)}\n"
                f"Please ensure Microsoft SQL Server is running and DATABASE_URL is properly configured."
            ) from e
    return _engine

def get_db_session():
    get_engine()
    return _SessionFactory()

def get_db_connection():
    engine = get_engine()
    return engine.connect()

def init_db():
    """
    Initializes SQL Server database schema. Creates all tables if they do not exist.
    Strictly raises RuntimeError if SQL Server is not reachable (no fallback to SQLite).
    """
    engine = get_engine()
    try:
        Base.metadata.create_all(engine)
        print("[Database] Microsoft SQL Server tables initialized successfully.")
    except Exception as e:
        raise RuntimeError(f"DATABASE INITIALIZATION ERROR: Failed creating SQL Server tables: {e}") from e


# --- Document Operations ---

def insert_document(doc_id: str, name: str, file_type: str, file_size: int = 0) -> str:
    session = get_db_session()
    try:
        doc = session.query(Document).filter_by(id=doc_id).first()
        if not doc:
            doc = Document(id=doc_id, name=name, file_type=file_type, file_size=file_size, chunk_count=0)
            session.add(doc)
        else:
            doc.name = name
            doc.file_type = file_type
            doc.file_size = file_size
        session.commit()
        return doc_id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def insert_chunks(chunks_data: List[Dict[str, Any]]):
    session = get_db_session()
    try:
        doc_chunk_counts: Dict[str, int] = {}
        for item in chunks_data:
            chunk_id = item.get("id", str(uuid.uuid4()))
            doc_id = item["document_id"]
            doc_name = item["document_name"]
            page_num = item.get("page_number")
            content = item["content"]
            embedding_blob = item["embedding"] # bytes

            chunk = Chunk(
                id=chunk_id,
                document_id=doc_id,
                document_name=doc_name,
                page_number=page_num,
                content=content,
                embedding=embedding_blob
            )
            session.add(chunk)
            doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1

        for doc_id, count in doc_chunk_counts.items():
            doc = session.query(Document).filter_by(id=doc_id).first()
            if doc:
                doc.chunk_count = (doc.chunk_count or 0) + count

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_documents() -> List[Dict[str, Any]]:
    session = get_db_session()
    try:
        docs = session.query(Document).order_by(desc(Document.created_at)).all()
        return [d.to_dict() for d in docs]
    finally:
        session.close()

def delete_document(doc_id: str) -> bool:
    session = get_db_session()
    try:
        doc = session.query(Document).filter_by(id=doc_id).first()
        if doc:
            session.delete(doc)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_chunks_with_embeddings() -> List[Dict[str, Any]]:
    session = get_db_session()
    try:
        chunks = session.query(Chunk).all()
        return [c.to_dict() for c in chunks]
    finally:
        session.close()


# --- Q&A Operations ---

def insert_qa_pair(qa_id: str, question: str, answer: str, source: str, embedding_bytes: bytes) -> str:
    session = get_db_session()
    try:
        qa = QAPair(
            id=qa_id,
            question=question,
            answer=answer,
            source=source,
            embedding=embedding_bytes
        )
        session.add(qa)
        session.commit()
        return qa_id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_qa_pairs() -> List[Dict[str, Any]]:
    session = get_db_session()
    try:
        qas = session.query(QAPair).order_by(desc(QAPair.created_at)).all()
        return [q.to_dict(include_embedding=False) for q in qas]
    finally:
        session.close()

def get_all_qa_with_embeddings() -> List[Dict[str, Any]]:
    session = get_db_session()
    try:
        qas = session.query(QAPair).all()
        return [q.to_dict(include_embedding=True) for q in qas]
    finally:
        session.close()

def delete_qa_pair(qa_id: str) -> bool:
    session = get_db_session()
    try:
        qa = session.query(QAPair).filter_by(id=qa_id).first()
        if qa:
            session.delete(qa)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# --- Conversation & Message Operations ---

def create_conversation(title: str = "New Conversation") -> str:
    conv_id = str(uuid.uuid4())
    session = get_db_session()
    try:
        conv = Conversation(id=conv_id, title=title)
        session.add(conv)
        session.commit()
        return conv_id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_conversations() -> List[Dict[str, Any]]:
    session = get_db_session()
    try:
        convs = session.query(Conversation).order_by(desc(Conversation.updated_at)).all()
        return [c.to_dict() for c in convs]
    finally:
        session.close()

def get_conversation(conv_id: str) -> Optional[Dict[str, Any]]:
    session = get_db_session()
    try:
        conv = session.query(Conversation).filter_by(id=conv_id).first()
        if not conv:
            return None
        res = conv.to_dict()
        messages = session.query(Message).filter_by(conversation_id=conv_id).order_by(Message.created_at.asc()).all()
        res["messages"] = [m.to_dict() for m in messages]
        return res
    finally:
        session.close()

def update_conversation_title(conv_id: str, title: str):
    session = get_db_session()
    try:
        conv = session.query(Conversation).filter_by(id=conv_id).first()
        if conv:
            conv.title = title
            conv.updated_at = datetime.utcnow()
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_conversation(conv_id: str) -> bool:
    session = get_db_session()
    try:
        conv = session.query(Conversation).filter_by(id=conv_id).first()
        if conv:
            session.delete(conv)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def insert_message(conv_id: str, role: str, content: str, sources: Optional[List[Dict[str, Any]]] = None) -> str:
    msg_id = str(uuid.uuid4())
    sources_json = json.dumps(sources) if sources else None
    session = get_db_session()
    try:
        msg = Message(
            id=msg_id,
            conversation_id=conv_id,
            role=role,
            content=content,
            sources=sources_json
        )
        session.add(msg)
        conv = session.query(Conversation).filter_by(id=conv_id).first()
        if conv:
            conv.updated_at = datetime.utcnow()
        session.commit()
        return msg_id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# --- Two-Way Communicative Knowledge Updates Operations ---

def get_next_update_number(session) -> int:
    max_num = session.query(func.max(KnowledgeUpdate.update_number)).scalar()
    return (max_num or 0) + 1

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
    session = get_db_session()
    try:
        update_id = str(uuid.uuid4())
        update_num = get_next_update_number(session)
        is_active = (status == "approved")
        approved_at = datetime.utcnow() if status == "approved" else None

        ku = KnowledgeUpdate(
            id=update_id,
            update_number=update_num,
            conversation_id=conversation_id,
            original_information=original_information,
            corrected_information=corrected_information,
            source_document=source_document,
            source_page=source_page,
            reason=reason,
            status=status,
            created_by=created_by,
            approved_at=approved_at,
            active=is_active,
            embedding=embedding
        )
        session.add(ku)
        session.commit()
        return ku.to_dict(include_embedding=False)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def approve_knowledge_update(update_id: str, embedding: Optional[bytes] = None) -> bool:
    session = get_db_session()
    try:
        ku = session.query(KnowledgeUpdate).filter_by(id=update_id).first()
        if ku:
            ku.status = "approved"
            ku.active = True
            ku.approved_at = datetime.utcnow()
            if embedding is not None:
                ku.embedding = embedding
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def reject_knowledge_update(update_id: str) -> bool:
    session = get_db_session()
    try:
        ku = session.query(KnowledgeUpdate).filter_by(id=update_id).first()
        if ku:
            ku.status = "rejected"
            ku.active = False
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def revert_knowledge_update(update_id: str) -> bool:
    session = get_db_session()
    try:
        ku = session.query(KnowledgeUpdate).filter_by(id=update_id).first()
        if ku:
            ku.status = "reverted"
            ku.active = False
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_knowledge_update(update_id: str) -> bool:
    session = get_db_session()
    try:
        ku = session.query(KnowledgeUpdate).filter_by(id=update_id).first()
        if ku:
            session.delete(ku)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_knowledge_updates() -> List[Dict[str, Any]]:
    session = get_db_session()
    try:
        updates = session.query(KnowledgeUpdate).order_by(desc(KnowledgeUpdate.created_at)).all()
        return [u.to_dict(include_embedding=False) for u in updates]
    finally:
        session.close()

def get_active_knowledge_updates() -> List[Dict[str, Any]]:
    session = get_db_session()
    try:
        updates = session.query(KnowledgeUpdate).filter(
            KnowledgeUpdate.status == "approved",
            KnowledgeUpdate.active == True
        ).all()
        return [u.to_dict(include_embedding=True) for u in updates]
    finally:
        session.close()

def get_knowledge_update_by_id(update_id: str) -> Optional[Dict[str, Any]]:
    session = get_db_session()
    try:
        ku = session.query(KnowledgeUpdate).filter_by(id=update_id).first()
        return ku.to_dict(include_embedding=True) if ku else None
    finally:
        session.close()

def get_pending_update_for_conversation(conv_id: str) -> Optional[Dict[str, Any]]:
    session = get_db_session()
    try:
        ku = session.query(KnowledgeUpdate).filter_by(
            conversation_id=conv_id,
            status="pending"
        ).order_by(desc(KnowledgeUpdate.created_at)).first()
        return ku.to_dict(include_embedding=False) if ku else None
    finally:
        session.close()


# --- Overall Stats ---

def get_stats() -> Dict[str, int]:
    session = get_db_session()
    try:
        doc_count = session.query(func.count(Document.id)).scalar() or 0
        chunk_count = session.query(func.count(Chunk.id)).scalar() or 0
        qa_count = session.query(func.count(QAPair.id)).scalar() or 0
        conv_count = session.query(func.count(Conversation.id)).scalar() or 0
        ku_count = session.query(func.count(KnowledgeUpdate.id)).filter(
            KnowledgeUpdate.status == "approved",
            KnowledgeUpdate.active == True
        ).scalar() or 0
        return {
            "documents": doc_count,
            "chunks": chunk_count,
            "qa_pairs": qa_count,
            "conversations": conv_count,
            "knowledge_updates": ku_count
        }
    finally:
        session.close()
