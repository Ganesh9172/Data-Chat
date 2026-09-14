from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SourceReference(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    snippet: str
    similarity: Optional[float] = None

class PowerBIReportContext(BaseModel):
    report_name: Optional[str] = None
    page_name: Optional[str] = None
    visual_title: Optional[str] = None
    selected_filters: Optional[Dict[str, Any]] = None
    data_summary: Optional[str] = None

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    report_context: Optional[PowerBIReportContext] = None

class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[SourceReference] = []

class QACreateRequest(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    source: str = Field("User Approved Q&A", min_length=1)

class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: Optional[List[Dict[str, Any]]] = []

class StatsResponse(BaseModel):
    documents: int
    chunks: int
    qa_pairs: int
    conversations: int
