# models.py - Sincronizado con Android
from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="user")
    productivity_logs = relationship("ProductivityLog", back_populates="user")
    suggestions = relationship("Suggestion", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Android fields
    priority = Column(String(20), default="medium")  # low, medium, high
    status = Column(String(20), default="pending")  # pending, in_progress, completed, cancelled
    due_date = Column(DateTime)  # Android usa due_date
    completed_at = Column(DateTime)

    # AI fields adicionales
    est_minutes = Column(Integer)  # Estimación de tiempo
    energy_req = Column(String(20))  # low, medium, high - energía requerida

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tasks")
    plan_steps = relationship("PlanStep", back_populates="task")
    suggestions = relationship("Suggestion", back_populates="task")
    activity_logs = relationship("ActivityLog", back_populates="task")


class PlanStep(Base):
    __tablename__ = "plan_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("plan_steps.id"))  # Para sub-pasos

    step_order = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, in_progress, completed, skipped

    # Campos adicionales para análisis
    est_minutes = Column(Integer)
    actual_minutes = Column(Integer)
    completed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="plan_steps")
    parent = relationship("PlanStep", remote_side=[id])


class ProductivityLog(Base):
    __tablename__ = "productivity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))

    # Métricas de productividad
    ts = Column(DateTime, default=datetime.utcnow)
    focus_score = Column(Float)  # 0.0 - 1.0
    energy_level = Column(Float)  # 0.0 - 1.0

    # Datos contextuales
    session_duration = Column(Integer)  # minutos
    interruptions = Column(Integer)
    mood = Column(String(20))  # great, good, ok, bad, terrible

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="productivity_logs")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))

    action = Column(String(100), nullable=False)  # task_created, task_completed, chat_interaction, etc.
    details = Column(JSON)  # Datos adicionales en JSON
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="users")  # Error aquí, debería ser diferente
    task = relationship("Task", back_populates="activity_logs")


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))

    message = Column(Text, nullable=False)  # Texto de la sugerencia
    suggestion_type = Column(String(50), default="general")  # general, productivity, planning, etc.

    # Metadatos de IA
    reason = Column(JSON)  # Razones del modelo
    confidence = Column(Float)  # 0.0 - 1.0

    # Estado
    is_applied = Column(Boolean, default=False)
    applied_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="suggestions")
    task = relationship("Task", back_populates="suggestions")