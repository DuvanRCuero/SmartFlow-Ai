# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Any, Dict, List
from datetime import datetime
from uuid import UUID

# ==================== AUTH SCHEMAS ====================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

# ==================== TASK SCHEMAS ====================

class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"  # low, medium, high
    status: str = "pending"   # pending, in_progress, completed, cancelled
    due_date: Optional[datetime] = None

class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

# ==================== AGENT SCHEMAS ====================

class AgentRequest(BaseModel):
    user_id: Optional[str] = None  # Se obtiene del token
    task_id: Optional[str] = None
    query: Optional[str] = None

class AgentResponse(BaseModel):
    result: Dict[str, Any]

class ErrorResponse(BaseModel):
    detail: str

# ==================== CHAT SCHEMAS ====================

class ChatMessageRequest(BaseModel):
    message: str
    task_id: Optional[str] = None
    chat_history: Optional[List[dict]] = None

class GeneratePlanRequest(BaseModel):
    task_id: str