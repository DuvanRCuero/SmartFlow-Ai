# agent.py

import os
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_community.llms import OpenAI  # IMPORT CORRECTO
from tools import get_task_info, get_recent_logs, insert_plan_steps, insert_suggestion, llm_generate

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Debes tener la variable OPENAI_API_KEY en el entorno")

# 1. Definimos las herramientas como objetos Tool de LangChain
tools = [
    Tool(
        name="get_task_info",
        func=get_task_info,
        description="Obtiene información de una tarea dado su task_id."
    ),
    Tool(
        name="get_recent_logs",
        func=get_recent_logs,
        description="Recupera los últimos 5 registros de productividad de un user_id."
    ),
    Tool(
        name="insert_plan_steps",
        func=insert_plan_steps,
        description="Inserta una lista de plan_steps en la base de datos para una tarea dada."
    ),
    Tool(
        name="insert_suggestion",
        func=insert_suggestion,
        description="Inserta una sugerencia en la tabla suggestions."
    ),
    Tool(
        name="llm_generate",
        func=llm_generate,
        description="Llama a OpenAI para generar texto a partir de un prompt."
    ),
]

# 2. Creamos la instancia de LLM
llm = OpenAI(
    temperature=0.7,
    model_name="gpt-4o-mini",  # o "gpt-3.5-turbo"
    openai_api_key=OPENAI_API_KEY,
    request_timeout=60
)

# 3. Inicializamos el agente con las tools y el LLM
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Ejemplo rápido de cómo probar en REPL:
# response = agent.run("Dame información de la tarea '123e4567-e89b-12d3-a456-426614174000'.")
# print(response)
