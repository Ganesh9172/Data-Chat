from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SourceReference(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    snippet: str
    similarity: Optional[float] = None
    original_source: Optional[str] = None
    is_knowledge_update: Optional[bool] = False

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
    is_correction_prompt: Optional[bool] = False
    pending_update_id: Optional[str] = None

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

class KnowledgeUpdateCreateRequest(BaseModel):
    original_information: str = Field(..., min_length=1)
    corrected_information: str = Field(..., min_length=1)
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    reason: Optional[str] = None
    status: Optional[str] = "approved"

class KnowledgeUpdateResponse(BaseModel):
    id: str
    update_number: Optional[int] = None
    conversation_id: Optional[str] = None
    original_information: str
    corrected_information: str
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    reason: Optional[str] = None
    status: str
    created_by: str
    created_at: Optional[str] = None
    approved_at: Optional[str] = None
    version: int
    active: bool

class StatsResponse(BaseModel):
    documents: int
    chunks: int
    qa_pairs: int
    conversations: int
    knowledge_updates: Optional[int] = 0
