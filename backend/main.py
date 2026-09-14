import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
    get_stats
)
from backend.models import (
    ChatRequest,
    ChatResponse,
    QACreateRequest,
    ConversationCreateRequest,
    ConversationResponse,
    StatsResponse
)
from backend.knowledge import (
    process_pdf_file,
    process_text_content,
    process_qa_entry,
    KNOWLEDGE_DATA_DIR
)
from backend.chat import generate_chat_response

# Initialize SQLite database tables
init_db()

app = FastAPI(
    title="Firebird AI Backend",
    description="Knowledge-Trained RAG Chatbot API with auto-updating knowledge base & Power BI integration readiness",
    version="1.0.0"
)

# Enable CORS for Vite frontend
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
        "stats": stats
    }

# --- Chat Endpoint ---
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    try:
        res = generate_chat_response(
            message=payload.message,
            conversation_id=payload.conversation_id,
            report_context=payload.report_context
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation failed: {str(e)}"
        )

# --- Knowledge Upload & Management ---
@app.post("/api/knowledge/upload")
async def upload_knowledge_file(file: UploadFile = File(...)):
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
            # Attempt to read as text
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
def add_qa_knowledge(payload: QACreateRequest):
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
def list_knowledge():
    docs = get_all_documents()
    qa = get_all_qa_pairs()
    stats = get_stats()
    return {
        "documents": docs,
        "qa_pairs": qa,
        "stats": stats
    }

@app.delete("/api/knowledge/{item_id}")
def remove_knowledge(item_id: str):
    # Try deleting document first
    if delete_document(item_id):
        return {"status": "success", "message": f"Document {item_id} removed"}
    # If not document, try deleting QA pair
    if delete_qa_pair(item_id):
        return {"status": "success", "message": f"Q&A pair {item_id} removed"}
    raise HTTPException(status_code=404, detail="Knowledge item not found")

# --- Conversation Management ---
@app.post("/api/chats")
def create_new_chat(payload: Optional[ConversationCreateRequest] = None):
    title = payload.title if payload and payload.title else "New Conversation"
    conv_id = create_conversation(title=title)
    return {"id": conv_id, "title": title}

@app.get("/api/chats")
def list_chats():
    return get_all_conversations()

@app.get("/api/chats/{chat_id}")
def get_chat_history(chat_id: str):
    conv = get_conversation(chat_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    success = delete_conversation(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "message": f"Conversation {chat_id} deleted"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
