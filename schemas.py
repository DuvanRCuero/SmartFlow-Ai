# schemas.py
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

# ---------- Requests ----------

class AgentRequest(BaseModel):
    """
    Payload que envía el cliente para que el agent lo procese. 
    Por simplicidad, consideramos que el cliente envía una 'query' genérica
    (p.ej. "Genera plan_steps para task X"), o bien datos estructurados.
    """
    user_id: UUID
    task_id: Optional[UUID] = None
    query: Optional[str] = None

# ---------- Responses ----------

class PlanStepOut(BaseModel):
    order: int
    text: str

class SuggestionOut(BaseModel):
    message: str
    reason: Optional[dict]
    confidence: Optional[float]
    suggestion_time: datetime

class AgentResponse(BaseModel):
    """
    La respuesta del agente, podría contener plan_steps, sugerencias, 
    o un texto libre, dependiendo del tipo de llamada.
    Para este ejemplo, retornaremos un JSON con un campo 'result'.
    """
    result: dict

class ErrorResponse(BaseModel):
    detail: str
