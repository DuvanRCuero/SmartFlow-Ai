# main.py

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID

from schemas import AgentRequest, AgentResponse, ErrorResponse
from agent import agent  # Importa el agente ya inicializado

app = FastAPI(
    title="SmartFlow Agent API",
    description="FastAPI local que expone un LangChain Agent para interactuar con la BD y OpenAI.",
    version="1.0.0"
)

# Permitir CORS en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringe esto a tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post(
    "/agent/run",
    response_model=AgentResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
def run_agent(req: AgentRequest):
    """
    Recibe un request con user_id, opcionalmente task_id y/o query.
    Luego construye una instrucción de texto para el agente y llama a agent.run().
    """
    # Validar user_id
    try:
        user_uuid = UUID(str(req.user_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Formato inválido de user_id.")

    # Construimos la instrucción que se pasa al agent
    instruction = f"UserId: {user_uuid}.\n"
    if req.task_id:
        try:
            task_uuid = UUID(str(req.task_id))
            instruction += f"TaskId: {task_uuid}.\n"
        except Exception:
            raise HTTPException(status_code=400, detail="Formato inválido de task_id.")

    if req.query:
        instruction += f"Pregunta: {req.query}\n"
    else:
        if not req.task_id:
            raise HTTPException(status_code=400, detail="Debes enviar al menos 'task_id' o 'query'.")
        instruction += (
            "Objetivo: Genera 4–6 pasos (plan_steps) detallados para la tarea indicada.\n"
            "Usa las herramientas disponibles: get_task_info, get_recent_logs, insert_plan_steps, llm_generate.\n"
            "Formato de salida: JSON con {'steps': [ {'order': int, 'text': str}, ... ]}."
        )

    try:
        # Ejecutamos el agente
        result_text = agent.run(instruction)

        # Intentamos parsear el resultado como JSON
        import json
        try:
            result_dict = json.loads(result_text)
        except Exception:
            result_dict = {"raw": result_text}

        return AgentResponse(result=result_dict)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al ejecutar el agente: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
