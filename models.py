# models.py
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    Float,
    ForeignKey,
    JSON,
    Boolean,
    SmallInteger,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    tz = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tasks = relationship("Task", back_populates="owner")
    logs = relationship("ProductivityLog", back_populates="owner")
    suggestions = relationship("Suggestion", back_populates="owner")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=True)  # Ajusta relación si existe tabla
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    est_minutes = Column(Integer, nullable=True)
    energy_req = Column(String(20), nullable=True)  # p.ej. 'low', 'medium', 'high'
    priority = Column(SmallInteger, nullable=True)  # 1..9
    state = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="tasks")
    plan_steps = relationship("PlanStep", back_populates="task")
    suggestions = relationship("Suggestion", back_populates="task")


class ProductivityLog(Base):
    __tablename__ = "productivity_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ts = Column(DateTime(timezone=True), server_default=func.now())  # timestamp
    focus_score = Column(Float, nullable=False)   # 0.0 – 1.0
    energy_level = Column(String(20), nullable=False)  # e.g. 'low', 'medium', 'high', 'peak'
    context = Column(JSON, nullable=True)  # Información adicional

    owner = relationship("User", back_populates="logs")


class PlanStep(Base):
    __tablename__ = "plan_steps"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("plan_steps.id"), nullable=True)
    step_order = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'in_progress', 'done'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="plan_steps")
    # relación recursiva de pasos hijos si la usas:
    children = relationship("PlanStep", remote_side=[id])


class Suggestion(Base):
    __tablename__ = "suggestions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    suggestion_time = Column(DateTime(timezone=True), server_default=func.now())
    message = Column(Text, nullable=False)      # texto de la sugerencia
    reason = Column(JSON, nullable=True)        # JSON con datos usados para justificar
    confidence = Column(Float, nullable=True)

    owner = relationship("User", back_populates="suggestions")
    task = relationship("Task", back_populates="suggestions")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metrics = Column(JSON, nullable=True)       # e.g. { "model": "...", "in_tokens": 123, ... }
    s3_uri = Column(String(512), nullable=True) # lugar donde se almacena payload completo
    created_at = Column(DateTime(timezone=True), server_default=func.now())
