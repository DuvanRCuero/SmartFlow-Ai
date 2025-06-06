# tools.py

import os
import json
from uuid import UUID

from sqlalchemy.orm import Session
from langchain.tools import tool
from langchain_community.llms import OpenAI  # IMPORT CORRECTO para la versión actual
from db import get_db
from models import Task, ProductivityLog, PlanStep, Suggestion

from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# -----------------------------------------------------------------------------
# 1) Tool: get_task_info
# -----------------------------------------------------------------------------
@tool(
    "get_task_info",
    description="Toma un task_id (UUID) y devuelve un JSON con los campos relevantes de la tarea: title, description, due_at, est_minutes, energy_req, priority."
)
def get_task_info(task_id_str: str) -> str:
    """
    Espera recibir task_id en cadena (string UUID).
    Devuelve un JSON string con la info de la tarea o un mensaje de error.
    """
    try:
        task_id = UUID(task_id_str)
    except Exception:
        return json.dumps({"error": "Formato de task_id inválido."})

    db: Session = next(get_db())
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return json.dumps({"error": f"Tarea con id {task_id} no existe."})

        result = {
            "id": str(task.id),
            "title": task.title,
            "description": task.description or "",
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "est_minutes": task.est_minutes,
            "energy_req": task.energy_req,
            "priority": task.priority,
        }
        return json.dumps(result)
    finally:
        db.close()


# -----------------------------------------------------------------------------
# 2) Tool: get_recent_logs
# -----------------------------------------------------------------------------
@tool(
    "get_recent_logs",
    description="Toma un user_id (UUID) y devuelve un JSON con los últimos 5 registros de productividad (ts, focus_score, energy_level)."
)
def get_recent_logs(user_id_str: str) -> str:
    """
    Espera recibir user_id en cadena (string UUID).
    Devuelve un JSON string con lista de últimos 5 logs ordenados por ts DESC.
    """
    try:
        user_id = UUID(user_id_str)
    except Exception:
        return json.dumps({"error": "Formato de user_id inválido."})

    db: Session = next(get_db())
    try:
        logs = (
            db.query(ProductivityLog)
            .filter(ProductivityLog.user_id == user_id)
            .order_by(ProductivityLog.ts.desc())
            .limit(5)
            .all()
        )
        out = []
        for log in logs:
            out.append({
                "ts": log.ts.isoformat(),
                "focus_score": log.focus_score,
                "energy_level": log.energy_level
            })
        return json.dumps(out)
    finally:
        db.close()


# -----------------------------------------------------------------------------
# 3) Tool: insert_plan_steps
# -----------------------------------------------------------------------------
@tool(
    "insert_plan_steps",
    description="Recibe un JSON con { task_id: str, steps: [ {order: int, text: str}, ... ] } e inserta cada paso en la tabla plan_steps. Devuelve un mensaje de éxito o error."
)
def insert_plan_steps(input_str: str) -> str:
    """
    input_str debe ser un JSON con estructura:
    {
      "task_id": "uuid-string",
      "steps": [
         {"order": 1, "text": "..."},
         {"order": 2, "text": "..."},
         ...
      ]
    }
    """
    try:
        payload = json.loads(input_str)
    except json.JSONDecodeError:
        return "Error: JSON inválido en insert_plan_steps."

    if "task_id" not in payload or "steps" not in payload:
        return "Error: Falta 'task_id' o 'steps' en el payload."

    try:
        task_id = UUID(payload["task_id"])
    except Exception:
        return "Error: task_id tiene formato inválido."

    db: Session = next(get_db())
    try:
        # Verificamos que la tarea exista
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return f"Error: No existe tarea con id {task_id}."

        # Insertamos cada paso
        for step in payload["steps"]:
            order = step.get("order")
            text = step.get("text")
            if order is None or text is None:
                return "Error: Cada step debe tener 'order' y 'text'."

            ps = PlanStep(
                task_id=task_id,
                parent_id=None,
                step_order=order,
                text=text,
                status="pending"
            )
            db.add(ps)

        db.commit()
        return f"Plan steps insertados exitosamente para task {task_id}."
    except Exception as e:
        db.rollback()
        return f"Error al insertar plan_steps: {str(e)}"
    finally:
        db.close()


# -----------------------------------------------------------------------------
# 4) Tool: insert_suggestion
# -----------------------------------------------------------------------------
@tool(
    "insert_suggestion",
    description="Recibe un JSON con { user_id: str, task_id: str (opcional), message: str, reason: dict (opcional), confidence: float (opcional) } y la inserta en la tabla suggestions. Retorna mensaje de confirmación o error."
)
def insert_suggestion(input_str: str) -> str:
    """
    input_str debe ser un JSON con:
    {
      "user_id": "uuid-string",
      "task_id": "uuid-string" (opcional),
      "message": "Texto de la sugerencia",
      "reason": { ... } (opcional),
      "confidence": 0.82  (opcional)
    }
    """
    try:
        payload = json.loads(input_str)
    except json.JSONDecodeError:
        return "Error: JSON inválido en insert_suggestion."

    if "user_id" not in payload or "message" not in payload:
        return "Error: Falta 'user_id' o 'message' en el payload."

    try:
        user_id = UUID(payload["user_id"])
    except Exception:
        return "Error: user_id tiene formato inválido."

    task_id = None
    if payload.get("task_id"):
        try:
            task_id = UUID(payload["task_id"])
        except Exception:
            return "Error: task_id tiene formato inválido."

    message = payload["message"]
    reason = payload.get("reason", None)
    confidence = payload.get("confidence", None)

    db: Session = next(get_db())
    try:
        new_sugg = Suggestion(
            user_id=user_id,
            task_id=task_id,
            message=message,
            reason=reason if isinstance(reason, dict) else None,
            confidence=confidence
        )
        db.add(new_sugg)
        db.commit()
        return f"Sugerencia insertada exitosamente (user {user_id})."
    except Exception as e:
        db.rollback()
        return f"Error al insertar sugerencia: {str(e)}"
    finally:
        db.close()


# -----------------------------------------------------------------------------
# 5) Tool: llm_generate
# -----------------------------------------------------------------------------
@tool(
    "llm_generate",
    description=(
        "Recibe en input un prompt de texto plano (string). Llama a OpenAI ChatCompletion "
        "con el modelo configurado y devuelve el contenido como string."
    )
)
def llm_generate(prompt: str) -> str:
    """
    Usa LangChain-Community OpenAI wrapper para enviar un único mensaje (sin herramientas adicionales).
    """
    llm = OpenAI(
        temperature=0.7,
        model_name="gpt-4o-mini",  # o "gpt-3.5-turbo" si no tienes acceso a GPT-4
        openai_api_key=OPENAI_API_KEY,
        request_timeout=60
    )
    try:
        response = llm(prompt)
        return response
    except Exception as e:
        return f"Error en llm_generate: {str(e)}"
