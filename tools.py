# tools_async.py - Tools para el agente que funcionan con AsyncPG
import os
import json
import asyncio
from uuid import UUID
from datetime import datetime
from typing import Optional

from langchain.tools import tool
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Pool de conexiones global
db_pool = None


def set_db_pool(pool):
    """Establece el pool de conexiones desde main.py"""
    global db_pool
    db_pool = pool


def run_async_query(query_func):
    """Wrapper para ejecutar funciones async desde herramientas sync"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(query_func())


@tool(
    "get_task_info",
    description="Obtiene información de una tarea por ID"
)
def get_task_info(task_id_str: str) -> str:
    async def query():
        try:
            task_id = UUID(task_id_str)
        except:
            return json.dumps({"error": "ID inválido"})

        if not db_pool:
            return json.dumps({"error": "BD no disponible"})

        async with db_pool.acquire() as conn:
            task = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1", task_id
            )

            if not task:
                return json.dumps({"error": "Tarea no encontrada"})

            return json.dumps({
                "id": str(task['id']),
                "title": task['title'],
                "description": task['description'],
                "priority": task['priority'],
                "status": task['status'],
                "due_date": task['due_date'].isoformat() if task['due_date'] else None
            })

    return run_async_query(query)


@tool(
    "create_task",
    description="Crea una nueva tarea. Formato: {user_id: 'uuid', title: 'texto', description: 'texto'}"
)
def create_task(input_str: str) -> str:
    async def query():
        try:
            payload = json.loads(input_str)
        except:
            return "Error: JSON inválido"

        if not payload.get("user_id") or not payload.get("title"):
            return "Error: Faltan user_id o title"

        try:
            user_id = UUID(payload["user_id"])
        except:
            return "Error: user_id inválido"

        if not db_pool:
            return "Error: BD no disponible"

        async with db_pool.acquire() as conn:
            task_id = await conn.fetchval(
                """INSERT INTO tasks (user_id, title, description, priority, status)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                user_id,
                payload["title"],
                payload.get("description", ""),
                payload.get("priority", "medium"),
                "pending"
            )

            return f"✅ Tarea creada con ID: {task_id}"

    return run_async_query(query)


@tool(
    "insert_plan_steps",
    description="Inserta pasos para una tarea. Formato: {task_id: 'uuid', steps: [{order: 1, text: 'paso'}, ...]}"
)
def insert_plan_steps(input_str: str) -> str:
    async def query():
        try:
            payload = json.loads(input_str)
        except:
            return "Error: JSON inválido"

        task_id = UUID(payload["task_id"])
        steps = payload["steps"]

        if not db_pool:
            return "Error: BD no disponible"

        async with db_pool.acquire() as conn:
            # Eliminar pasos existentes
            await conn.execute("DELETE FROM plan_steps WHERE task_id = $1", task_id)

            # Insertar nuevos pasos
            for step in steps:
                await conn.execute(
                    """INSERT INTO plan_steps (task_id, step_order, text, status)
                       VALUES ($1, $2, $3, $4)""",
                    task_id, step["order"], step["text"], "pending"
                )

            return f"✅ {len(steps)} pasos insertados"

    return run_async_query(query)


@tool(
    "llm_generate",
    description="Genera contenido adicional con IA"
)
def llm_generate(prompt: str) -> str:
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY,
            max_tokens=500
        )

        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Error: {str(e)}"


# Lista de herramientas
tools = [
    get_task_info,
    create_task,
    insert_plan_steps,
    llm_generate
]