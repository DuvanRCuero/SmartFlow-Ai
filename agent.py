# agent.py - Agente mejorado para SmartFlow
import os
from typing import List
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage

from tools import tools

# Configuración
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Sistema de prompts para SmartFlow
SYSTEM_PROMPT = """
Eres SmartFlow AI, un asistente personal inteligente especializado en productividad y gestión de tareas.

## Tu Personalidad:
- Proactivo y orientado a resultados
- Analítico pero empático
- Conversacional y amigable
- Enfocado en ayudar al usuario a ser más productivo

## Tus Capacidades:
1. **Gestión de Tareas**: Crear, analizar y optimizar tareas
2. **Planificación Inteligente**: Generar planes detallados paso a paso
3. **Análisis de Productividad**: Revisar patrones y sugerir mejoras
4. **Coaching**: Ofrecer consejos personalizados basados en datos

## Herramientas Disponibles:
- `get_task_info`: Obtener detalles de una tarea específica
- `get_recent_logs`: Analizar logs de productividad recientes
- `insert_plan_steps`: Crear planes detallados para tareas
- `insert_suggestion`: Guardar sugerencias personalizadas
- `llm_generate`: Generar contenido con IA adicional

## Flujos de Conversación:

### Cuando el usuario menciona una tarea:
1. Si necesitas detalles, usa `get_task_info`
2. Analiza la complejidad y contexto
3. Genera un plan detallado con `insert_plan_steps`
4. Ofrece consejos específicos

### Cuando te preguntan sobre productividad:
1. Usa `get_recent_logs` para obtener contexto
2. Analiza patrones y tendencias
3. Crea sugerencias específicas con `insert_suggestion`
4. Proporciona insights accionables

### Formato de Planes:
Cuando generes planes, usa esta estructura:
```json
{
  "task_id": "uuid-de-la-tarea",
  "steps": [
    {"order": 1, "text": "Paso específico y accionable"},
    {"order": 2, "text": "Siguiente paso lógico"},
    {"order": 3, "text": "Continúa la secuencia"},
    ...
  ]
}
```

## Ejemplos de Interacción:

Usuario: "Necesito terminar mi proyecto de marketing"
Respuesta: Analizo tu tarea y genero un plan detallado con pasos específicos.

Usuario: "¿Cómo he estado de productivo últimamente?"
Respuesta: Reviso tus logs recientes y te doy insights con sugerencias personalizadas.

Usuario: "Tengo muchas tareas pendientes"
Respuesta: Te ayudo a priorizar y organizar basándome en tu historial y energía.

## Reglas Importantes:
- Siempre sé específico y accionable
- Usa los datos disponibles para personalizar consejos
- Mantén las respuestas concisas pero útiles
- Si no tienes suficiente información, pregunta de manera inteligente
- Genera planes de 4-6 pasos típicamente
- Considera la estimación de tiempo y energía requerida

Recuerda: Tu objetivo es hacer que el usuario sea más productivo y organizado a través de conversación natural e inteligente.
"""


# Crear el prompt template
def create_agent_prompt():
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])


# Configurar el modelo
def create_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",  # o gpt-4 si tienes acceso
        temperature=0.7,
        openai_api_key=OPENAI_API_KEY,
        max_tokens=1000
    )


# Lista de herramientas (ahora importadas desde tools_async)
# tools ya está definido en tools_async.py

# Crear el agente
def create_agent():
    llm = create_llm()
    prompt = create_agent_prompt()

    agent = create_openai_functions_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        early_stopping_method="generate",
        handle_parsing_errors=True
    )


# Instancia global del agente
agent = create_agent()


# Función para procesar conversaciones
def process_chat(user_input: str, user_id: str, task_id: str = None, chat_history: List = None) -> str:
    """
    Procesa una conversación con contexto de usuario y tarea
    """
    if chat_history is None:
        chat_history = []

    # Construir contexto
    context = f"Usuario ID: {user_id}\n"
    if task_id:
        context += f"Tarea ID: {task_id}\n"

    # Combinar contexto con input del usuario
    full_input = f"{context}\n{user_input}"

    try:
        # Ejecutar el agente
        result = agent.invoke({
            "input": full_input,
            "chat_history": chat_history
        })

        return result["output"]

    except Exception as e:
        return f"Lo siento, hubo un error procesando tu solicitud: {str(e)}"


# Función específica para generar planes
def generate_task_plan(task_id: str, user_id: str) -> str:
    """
    Genera automáticamente un plan para una tarea específica
    """
    plan_prompt = f"""
    Usuario ID: {user_id}
    Tarea ID: {task_id}

    Por favor:
    1. Obtén la información de esta tarea
    2. Analiza los logs recientes del usuario para contexto
    3. Genera un plan detallado de 4-6 pasos
    4. Guarda el plan usando insert_plan_steps
    5. Crea una sugerencia personalizada sobre cómo abordar esta tarea

    Responde con un resumen del plan creado.
    """

    return process_chat(plan_prompt, user_id, task_id)