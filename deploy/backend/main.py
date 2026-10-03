import os
import shutil
import uuid
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from backend.database import (
    init_db,
    get_all_documents,
    delete_document,
    get_all_qa_pairs,
    delete_qa_pair,
    create_conversation,
    get_all_conversations,
    get_conversation,
    delete_conversation,
    get_stats,
    create_knowledge_update,
    approve_knowledge_update,
    reject_knowledge_update,
    revert_knowledge_update,
    delete_knowledge_update,
    get_all_knowledge_updates,
    get_knowledge_update_by_id
)
from backend.models import (
    ChatRequest,
    ChatResponse,
    QACreateRequest,
    ConversationCreateRequest,
    ConversationResponse,
    StatsResponse,
    KnowledgeUpdateCreateRequest,
    KnowledgeUpdateResponse,
    LoginRequest,
    LoginResponse,
    AdminLoginRequest,
    AdminLoginResponse
)
from backend.auth import (
    verify_admin_credentials,
    create_admin_token,
    get_optional_admin,
    require_admin
)
from backend.knowledge import (
    process_pdf_file,
    process_text_content,
    process_qa_entry,
    KNOWLEDGE_DATA_DIR,
    init_knowledge_base
)
from backend.chat import generate_chat_response
from backend.embeddings import get_embedding, vector_to_bytes



app = FastAPI(
    title="Firebird AI Backend",
    description="Knowledge-Trained RAG Chatbot API with Admin-only Knowledge Management and Session-Isolated Chat Privacy",
    version="2.2.0"
)


@app.on_event("startup")
async def startup_event():
    init_db()

    # Run knowledge-base initialization in the background
    # so the API can start accepting requests immediately.
    asyncio.create_task(
        asyncio.to_thread(init_knowledge_base)
    )

    
# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health & Stats ---
@app.get("/api/health")
def health_check():
    stats = get_stats()
    return {
        "status": "online",
        "service": "Firebird AI",
        "database": "JSON File Storage",
        "stats": stats
    }

# --- Admin Authentication Endpoints ---
@app.post("/api/admin/login", response_model=AdminLoginResponse)
@app.post("/api/auth/login", response_model=AdminLoginResponse)
def admin_login_endpoint(payload: LoginRequest):
    """
    Authenticate administrator using credentials verified against environment variables.
    Returns signed Admin JWT access token.
    """
    username = payload.username or payload.email
    if not verify_admin_credentials(payload.password, username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )

    token = create_admin_token()
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "ADMIN",
        "name": "System Administrator"
    }

@app.get("/api/admin/me")
@app.get("/api/auth/me")
def get_admin_profile(admin: Dict[str, Any] = Depends(require_admin)):
    """Validates active Admin token and returns Admin profile."""
    return {
        "role": admin.get("role", "ADMIN"),
        "name": admin.get("name", "System Administrator"),
        "username": admin.get("username", "admin"),
        "authenticated": True
    }

# --- Knowledge Upload & Management (Admin-Only) ---
@app.post("/api/knowledge/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    admin: Dict[str, Any] = Depends(require_admin)
):
    filename = file.filename or "uploaded_document"
    ext = os.path.splitext(filename)[1].lower()

    file_path = os.path.join(KNOWLEDGE_DATA_DIR, filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        if ext == ".pdf":
            result = process_pdf_file(file_path, filename)
        elif ext in [".txt", ".md", ".csv", ".json", ".log"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            result = process_text_content(content, filename, file_type=ext.replace(".", ""))
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            result = process_text_content(content, filename, file_type="text")

        return {
            "status": "success",
            "message": f"Successfully indexed '{filename}'",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index document: {str(e)}")

@app.post("/api/knowledge/qa")
def add_qa_knowledge(
    payload: QACreateRequest,
    admin: Dict[str, Any] = Depends(require_admin)
):
    try:
        res = process_qa_entry(
            question=payload.question,
            answer=payload.answer,
            source=payload.source
        )
        return {
            "status": "success",
            "message": "Approved Q&A added to knowledge base",
            "data": res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index Q&A: {str(e)}")

@app.get("/api/knowledge")
def list_knowledge(admin: Optional[Dict[str, Any]] = Depends(get_optional_admin)):
    """Returns indexed knowledge. Full management view available to admin."""
    docs = get_all_documents()
    qa = get_all_qa_pairs()
    updates = get_all_knowledge_updates()
    stats = get_stats()
    return {
        "documents": docs,
        "qa_pairs": qa,
        "knowledge_updates": updates,
        "stats": stats
    }

# --- Knowledge Updates Endpoints (Admin-Only) ---
@app.get("/api/knowledge/updates", response_model=List[KnowledgeUpdateResponse])
def list_knowledge_updates(admin: Dict[str, Any] = Depends(require_admin)):
    return get_all_knowledge_updates()

@app.post("/api/knowledge/updates", response_model=KnowledgeUpdateResponse)
def create_update(
    payload: KnowledgeUpdateCreateRequest,
    admin: Dict[str, Any] = Depends(require_admin)
):
    try:
        emb = None
        if payload.status == "approved":
            emb = vector_to_bytes(get_embedding(f"{payload.original_information} {payload.corrected_information}"))
        ku = create_knowledge_update(
            original_information=payload.original_information,
            corrected_information=payload.corrected_information,
            source_document=payload.source_document,
            source_page=payload.source_page,
            reason=payload.reason,
            status=payload.status or "approved",
            created_by="admin",
            embedding=emb
        )
        return ku
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create knowledge update: {str(e)}")

@app.post("/api/knowledge/updates/{update_id}/approve")
def approve_update(
    update_id: str,
    admin: Dict[str, Any] = Depends(require_admin)
):
    ku = get_knowledge_update_by_id(update_id)
    if not ku:
        raise HTTPException(status_code=404, detail="Knowledge update not found")
    emb = vector_to_bytes(get_embedding(f"{ku['original_information']} {ku['corrected_information']}"))
    success = approve_knowledge_update(update_id, embedding=emb)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to approve update")
    return {"status": "success", "message": f"Update {update_id} approved and indexed"}

@app.post("/api/knowledge/updates/{update_id}/reject")
def reject_update(
    update_id: str,
    admin: Dict[str, Any] = Depends(require_admin)
):
    success = reject_knowledge_update(update_id)
    if not success:
        raise HTTPException(status_code=404, detail="Knowledge update not found")
    return {"status": "success", "message": f"Update {update_id} rejected"}

@app.post("/api/knowledge/updates/{update_id}/revert")
def revert_update(
    update_id: str,
    admin: Dict[str, Any] = Depends(require_admin)
):
    success = revert_knowledge_update(update_id)
    if not success:
        raise HTTPException(status_code=404, detail="Knowledge update not found")
    return {"status": "success", "message": f"Update {update_id} reverted"}

@app.delete("/api/knowledge/updates/{update_id}")
def delete_update(
    update_id: str,
    admin: Dict[str, Any] = Depends(require_admin)
):
    success = delete_knowledge_update(update_id)
    if not success:
        raise HTTPException(status_code=404, detail="Knowledge update not found")
    return {"status": "success", "message": f"Update {update_id} deleted"}

@app.delete("/api/knowledge/{item_id}")
def remove_knowledge(
    item_id: str,
    admin: Dict[str, Any] = Depends(require_admin)
):
    # Check if target is a document
    docs = get_all_documents()
    is_doc = any(d.get("id") == item_id for d in docs)
    if is_doc:
        if delete_document(item_id):
            return {"status": "success", "message": f"Document {item_id} removed"}

    # Check if target is a QA pair
    qas = get_all_qa_pairs()
    is_qa = any(q.get("id") == item_id for q in qas)
    if is_qa:
        if delete_qa_pair(item_id):
            return {"status": "success", "message": f"Q&A pair {item_id} removed"}

    # Check if target is a knowledge update
    kus = get_all_knowledge_updates()
    is_ku = any(u.get("id") == item_id for u in kus)
    if is_ku:
        if delete_knowledge_update(item_id):
            return {"status": "success", "message": f"Knowledge update {item_id} removed"}

    raise HTTPException(status_code=404, detail="Knowledge item not found")

# --- Chat & Conversation Endpoints (Session-Isolated & Publicly Accessible) ---
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    admin: Optional[Dict[str, Any]] = Depends(get_optional_admin)
):
    is_admin = admin is not None
    session_id = x_session_id.strip() if x_session_id and x_session_id.strip() else None

    # Verify conversation ownership if conversation_id is provided
    if payload.conversation_id:
        conv = get_conversation(payload.conversation_id)
        if conv and not is_admin:
            conv_owner = conv.get("session_id") or conv.get("user_id")
            if conv_owner and session_id and conv_owner != session_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You do not have access to this conversation"
                )

    effective_user = "admin" if is_admin and not session_id else (session_id or "default-visitor")

    try:
        res = generate_chat_response(
            message=payload.message,
            conversation_id=payload.conversation_id,
            report_context=payload.report_context,
            user_id=effective_user,
            is_admin=is_admin
        )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation failed: {str(e)}"
        )

@app.post("/api/chats")
@app.post("/api/conversations")
def create_new_chat(
    payload: Optional[ConversationCreateRequest] = None,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    admin: Optional[Dict[str, Any]] = Depends(get_optional_admin)
):
    is_admin = admin is not None
    session_id = x_session_id.strip() if x_session_id and x_session_id.strip() else None
    owner_id = "admin" if is_admin and not session_id else (session_id or f"sess_{uuid.uuid4().hex[:12]}")
    title = payload.title if payload and payload.title else "New Conversation"

    conv_id = create_conversation(title=title, user_id=owner_id, session_id=owner_id)
    return {"id": conv_id, "session_id": owner_id, "title": title}

@app.get("/api/chats")
@app.get("/api/conversations")
def list_chats(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    admin: Optional[Dict[str, Any]] = Depends(get_optional_admin)
):
    is_admin = admin is not None
    session_id = x_session_id.strip() if x_session_id and x_session_id.strip() else None

    # Normal users without session_id get empty list, preventing exposure of all users' chats
    return get_all_conversations(session_id=session_id, is_admin=is_admin, view_all=is_admin)

@app.get("/api/chats/{chat_id}")
@app.get("/api/conversations/{chat_id}")
def get_chat_history(
    chat_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    admin: Optional[Dict[str, Any]] = Depends(get_optional_admin)
):
    conv = get_conversation(chat_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_admin = admin is not None
    session_id = x_session_id.strip() if x_session_id and x_session_id.strip() else None

    if not is_admin:
        owner = conv.get("session_id") or conv.get("user_id")
        if not session_id or (owner and owner != session_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have access to this conversation"
            )
    return conv

@app.delete("/api/chats/{chat_id}")
@app.delete("/api/conversations/{chat_id}")
def delete_chat(
    chat_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    admin: Optional[Dict[str, Any]] = Depends(get_optional_admin)
):
    conv = get_conversation(chat_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_admin = admin is not None
    session_id = x_session_id.strip() if x_session_id and x_session_id.strip() else None

    if not is_admin:
        owner = conv.get("session_id") or conv.get("user_id")
        if not session_id or (owner and owner != session_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to delete this conversation"
            )

    success = delete_conversation(chat_id, session_id=session_id, is_admin=is_admin)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "message": f"Conversation {chat_id} deleted"}

# --- Static Frontend Serving (Unified Full-Stack Deployment) ---
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")

if os.path.exists(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Exclude API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        target_file = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.exists(target_file) and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
