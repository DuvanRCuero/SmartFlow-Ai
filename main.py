# main.py - Backend actualizado
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from typing import Optional, List
import hashlib
import jwt
import asyncpg
import os
from contextlib import asynccontextmanager

from db import DATABASE_URL, SECRET_KEY
from schemas import *  # Todos los schemas
from agent import agent, process_chat, generate_task_plan  # Tu agente LangChain
from tools import set_db_pool



# Variables globales para la conexión a BD
db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    # ✅ CRÍTICO: Establecer el pool para las herramientas del agente
    set_db_pool(db_pool)

    yield
    # Shutdown
    await db_pool.close()


app = FastAPI(
    title="SmartFlow API",
    description="API completa para SmartFlow con autenticación y agente IA",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


# Utilidades
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {"user_id": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


# ==================== AUTH ENDPOINTS ====================

@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, password_hash FROM users WHERE email = $1",
            request.email
        )

        if not user or user['password_hash'] != hash_password(request.password):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        token = create_access_token(str(user['id']))

        return LoginResponse(
            token=token,
            user=UserResponse(
                id=str(user['id']),
                email=user['email'],
                name=user['name']
            )
        )


@app.post("/auth/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    async with db_pool.acquire() as conn:
        # Verificar si el email ya existe
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", request.email)
        if existing:
            raise HTTPException(status_code=400, detail="El email ya está registrado")

        # Crear usuario
        user_id = str(uuid4())
        await conn.execute(
            "INSERT INTO users (id, email, name, password_hash) VALUES ($1, $2, $3, $4)",
            user_id, request.email, request.name, hash_password(request.password)
        )

        token = create_access_token(user_id)

        return LoginResponse(
            token=token,
            user=UserResponse(
                id=user_id,
                email=request.email,
                name=request.name
            )
        )


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name FROM users WHERE id = $1",
            UUID(current_user)
        )
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return UserResponse(
            id=str(user['id']),
            email=user['email'],
            name=user['name']
        )


# ==================== TASK ENDPOINTS ====================

@app.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(current_user: str = Depends(get_current_user)):
    async with db_pool.acquire() as conn:
        tasks = await conn.fetch(
            """SELECT id, title, description, priority, status, due_date, 
               completed_at, created_at, updated_at 
               FROM tasks WHERE user_id = $1 ORDER BY created_at DESC""",
            UUID(current_user)
        )

        return [TaskResponse(
            id=str(task['id']),
            title=task['title'],
            description=task['description'],
            priority=task['priority'],
            status=task['status'],
            due_date=task['due_date'],
            completed_at=task['completed_at'],
            created_at=task['created_at'],
            updated_at=task['updated_at']
        ) for task in tasks]


@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest, current_user: str = Depends(get_current_user)):
    async with db_pool.acquire() as conn:
        task_id = str(uuid4())

        await conn.execute(
            """INSERT INTO tasks (id, user_id, title, description, priority, status, due_date)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            task_id, UUID(current_user), request.title, request.description,
            request.priority, request.status, request.due_date
        )

        # Log de actividad
        await conn.execute(
            """INSERT INTO activity_logs (user_id, task_id, action, details)
               VALUES ($1, $2, $3, $4)""",
            UUID(current_user), UUID(task_id), "task_created",
            {"title": request.title}
        )

        # Obtener la tarea creada
        task = await conn.fetchrow(
            """SELECT id, title, description, priority, status, due_date,
               completed_at, created_at, updated_at FROM tasks WHERE id = $1""",
            UUID(task_id)
        )

        return TaskResponse(
            id=str(task['id']),
            title=task['title'],
            description=task['description'],
            priority=task['priority'],
            status=task['status'],
            due_date=task['due_date'],
            completed_at=task['completed_at'],
            created_at=task['created_at'],
            updated_at=task['updated_at']
        )


@app.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
        task_id: str,
        request: UpdateTaskRequest,
        current_user: str = Depends(get_current_user)
):
    async with db_pool.acquire() as conn:
        # Verificar que la tarea pertenece al usuario
        task = await conn.fetchrow(
            "SELECT * FROM tasks WHERE id = $1 AND user_id = $2",
            UUID(task_id), UUID(current_user)
        )

        if not task:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        # Construir la consulta de actualización dinámicamente
        updates = []
        values = []
        param_count = 1

        if request.title is not None:
            updates.append(f"title = ${param_count}")
            values.append(request.title)
            param_count += 1

        if request.description is not None:
            updates.append(f"description = ${param_count}")
            values.append(request.description)
            param_count += 1

        if request.priority is not None:
            updates.append(f"priority = ${param_count}")
            values.append(request.priority)
            param_count += 1

        if request.status is not None:
            updates.append(f"status = ${param_count}")
            values.append(request.status)
            param_count += 1

            # Si se marca como completada, agregar timestamp
            if request.status == "completed":
                updates.append(f"completed_at = ${param_count}")
                values.append(datetime.utcnow())
                param_count += 1

        if request.due_date is not None:
            updates.append(f"due_date = ${param_count}")
            values.append(request.due_date)
            param_count += 1

        if updates:
            query = f"""UPDATE tasks SET {', '.join(updates)}, updated_at = NOW() 
                       WHERE id = ${param_count} AND user_id = ${param_count + 1}"""
            values.extend([UUID(task_id), UUID(current_user)])

            await conn.execute(query, *values)

            # Log de actividad
            await conn.execute(
                """INSERT INTO activity_logs (user_id, task_id, action, details)
                   VALUES ($1, $2, $3, $4)""",
                UUID(current_user), UUID(task_id), "task_updated",
                request.dict(exclude_unset=True)
            )

        # Obtener la tarea actualizada
        updated_task = await conn.fetchrow(
            """SELECT id, title, description, priority, status, due_date,
               completed_at, created_at, updated_at FROM tasks WHERE id = $1""",
            UUID(task_id)
        )

        return TaskResponse(
            id=str(updated_task['id']),
            title=updated_task['title'],
            description=updated_task['description'],
            priority=updated_task['priority'],
            status=updated_task['status'],
            due_date=updated_task['due_date'],
            completed_at=updated_task['completed_at'],
            created_at=updated_task['created_at'],
            updated_at=updated_task['updated_at']
        )


# ==================== CHAT/AGENT ENDPOINTS ====================

@app.post("/chat/message", response_model=dict)
async def chat_message(
        request: ChatMessageRequest,
        current_user: str = Depends(get_current_user)
):
    """
    Endpoint principal para chat con el agente IA
    """
    try:
        # Procesar mensaje con agente
        response = process_chat(
            user_input=request.message,
            user_id=current_user,
            task_id=request.task_id,
            chat_history=request.chat_history or []
        )

        # Log de la interacción
        async with db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO activity_logs (user_id, task_id, action, details)
                   VALUES ($1, $2, $3, $4)""",
                UUID(current_user),
                UUID(request.task_id) if request.task_id else None,
                "chat_interaction",
                {
                    "user_message": request.message,
                    "ai_response": response[:500]  # Truncar para el log
                }
            )

        return {
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en chat: {str(e)}")


@app.post("/agent/generate-plan", response_model=dict)
async def generate_plan(
        request: GeneratePlanRequest,
        current_user: str = Depends(get_current_user)
):
    """
    Genera automáticamente un plan para una tarea
    """
    try:
        # Verificar que la tarea pertenece al usuario
        async with db_pool.acquire() as conn:
            task = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1 AND user_id = $2",
                UUID(request.task_id), UUID(current_user)
            )

            if not task:
                raise HTTPException(status_code=404, detail="Tarea no encontrada")

        # Generar plan con el agente
        plan_summary = generate_task_plan(request.task_id, current_user)

        return {
            "task_id": request.task_id,
            "plan_summary": plan_summary,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando plan: {str(e)}")


@app.get("/tasks/{task_id}/plan", response_model=List[dict])
async def get_task_plan(
        task_id: str,
        current_user: str = Depends(get_current_user)
):
    """
    Obtiene el plan de pasos de una tarea
    """
    async with db_pool.acquire() as conn:
        # Verificar que la tarea pertenece al usuario
        task = await conn.fetchrow(
            "SELECT * FROM tasks WHERE id = $1 AND user_id = $2",
            UUID(task_id), UUID(current_user)
        )

        if not task:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        # Obtener pasos del plan
        steps = await conn.fetch(
            """SELECT id, step_order, text, status, est_minutes, actual_minutes, 
               completed_at, created_at FROM plan_steps 
               WHERE task_id = $1 ORDER BY step_order""",
            UUID(task_id)
        )

        return [dict(step) for step in steps]


# ==================== LOGS Y SUGERENCIAS ====================

@app.get("/logs", response_model=List[dict])
async def get_activity_logs(
        limit: int = 50,
        current_user: str = Depends(get_current_user)
):
    async with db_pool.acquire() as conn:
        logs = await conn.fetch(
            """SELECT id, task_id, action, details, timestamp
               FROM activity_logs WHERE user_id = $1 
               ORDER BY timestamp DESC LIMIT $2""",
            UUID(current_user), limit
        )

        return [dict(log) for log in logs]


@app.get("/suggestions", response_model=List[dict])
async def get_suggestions(current_user: str = Depends(get_current_user)):
    async with db_pool.acquire() as conn:
        suggestions = await conn.fetch(
            """SELECT id, task_id, suggestion_text, suggestion_type, 
               is_applied, created_at FROM suggestions 
               WHERE user_id = $1 ORDER BY created_at DESC""",
            UUID(current_user)
        )

        return [dict(suggestion) for suggestion in suggestions]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)