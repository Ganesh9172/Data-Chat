from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SourceReference(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
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

class RelatedVideo(BaseModel):
    title: str
    url: str
    thumbnail_url: str
    video_id: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[SourceReference] = []
    is_correction_prompt: Optional[bool] = False
    pending_update_id: Optional[str] = None
    related_video: Optional[RelatedVideo] = None
    is_ground_truth_verified: Optional[bool] = False

class QACreateRequest(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    source: str = Field("User Approved Q&A", min_length=1)

class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: str
    created_at: str
    updated_at: str
    messages: Optional[List[Dict[str, Any]]] = []

class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1)
    email: Optional[str] = None
    username: Optional[str] = None

class AdminLoginRequest(BaseModel):
    password: str = Field(..., min_length=1)
    username: Optional[str] = None

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "ADMIN"
    name: Optional[str] = "System Administrator"

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    active: bool
    created_at: Optional[str] = None
    permissions: Dict[str, bool] = {}

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = "ADMIN"
    user: Optional[Dict[str, Any]] = None

class UserCreateRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)
    name: str = Field(..., min_length=1)
    role: Optional[str] = "USER"

class PermissionsUpdateRequest(BaseModel):
    permissions: Dict[str, bool]

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
