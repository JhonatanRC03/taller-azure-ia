"""
Laboratorio 11 - Orquestación multiagente secuencial con Agent Framework

Idea central:
-------------
Hasta ahora (lab09, lab10) siempre trabajaste con UN solo agente que hace
todo: recibe el prompt, decide si usa una herramienta, y responde. Aquí
aprendes el patrón de **múltiples agentes especializados** que colaboran
en cadena, cada uno haciendo una sola cosa bien:

  comentario del cliente
        │
        ▼
  [resumidor] → resume el comentario en una frase
        │
        ▼
  [clasificador] → clasifica ese resumen en una categoría
        │
        ▼
  [accion] → sugiere qué hacer a partir del resumen + la categoría
        │
        ▼
  respuesta final (con la salida de los 3 agentes)

Conceptos clave:
- `chat_client.as_agent(name=, instructions=)`: forma abreviada de crear un
  `Agent` a partir de un `FoundryChatClient` ya existente, sin tener que
  volver a pasarle el `client=` explícitamente cada vez (útil cuando varios
  agentes comparten el mismo cliente/modelo).
- `SequentialBuilder(participants=[...], output_from="all")`: arma una
  **orquestación secuencial** (un tipo de "workflow" multiagente): cada
  agente de la lista recibe la salida del anterior como entrada, en el
  orden en que aparecen en `participants`. `output_from="all"` hace que el
  resultado final incluya la respuesta de CADA agente, no solo la del
  último.
- `workflow.run(prompt)`: ejecuta la cadena completa de principio a fin.
- `resultado.get_outputs()`: devuelve la lista de resultados intermedios y
  final (uno por cada agente que participó), listos para inspeccionar.

Este patrón es útil cuando quieres dividir una tarea compleja en pasos más
simples y auditables, en vez de pedirle a un solo agente que "haga todo de
una vez" con un prompt gigante.
"""

import os
import asyncio
from pathlib import Path
from typing import cast
from dotenv import load_dotenv

# Add references
from agent_framework import Message
from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import SequentialBuilder
from azure.identity import AzureCliCredential

load_dotenv(Path(__file__).parent / ".env")


# Instrucciones de cada agente especializado (en español, tema tienda de telescopios)
instrucciones_resumidor = """Eres un asistente que resume comentarios de clientes de una tienda de
telescopios. Lee el comentario y devuelve un resumen de una sola frase, claro y objetivo,
sin agregar opiniones propias."""

instrucciones_clasificador = """Eres un asistente que clasifica comentarios de clientes en UNA sola
categoría de esta lista: 'Solicitud de función', 'Queja', 'Elogio' o 'Reporte de error'.
Responde únicamente con el nombre de la categoría, sin explicaciones adicionales."""

instrucciones_accion = """Eres un asistente que, a partir de un comentario de cliente ya resumido y
clasificado, sugiere una única acción concreta y breve que el equipo debería tomar.
Responde con una sola frase."""


async def main():
    # Create the chat client
    credential = AzureCliCredential()
    chat_client = FoundryChatClient(
        credential=credential,
        project_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
        model=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME"),
    )

    # Create agents
    resumidor_agente = chat_client.as_agent(
        name="resumidor",
        instructions=instrucciones_resumidor,
    )

    clasificador_agente = chat_client.as_agent(
        name="clasificador",
        instructions=instrucciones_clasificador,
    )

    accion_agente = chat_client.as_agent(
        name="accion",
        instructions=instrucciones_accion,
    )

    # Initialize the current feedback
    comentario = """
    Uso la app de la tienda de telescopios todas las noches para revisar el inventario y en
    general funciona muy bien. Pero cuando trabajo tarde en la noche, la pantalla tan brillante
    me molesta mucho la vista. Si agregaran un modo oscuro, la experiencia sería mucho más
    cómoda.
    """

    # Build sequential orchestration
    workflow = SequentialBuilder(
        participants=[resumidor_agente, clasificador_agente, accion_agente],
        output_from="all",
    ).build()

    # Run and collect outputs
    resultado = await workflow.run(f"Comentario del cliente: {comentario}")
    salidas = resultado.get_outputs()

    # Display outputs
    i = 1
    for respuesta in salidas:
        for msg in cast(list[Message], respuesta.messages):
            nombre = msg.author_name or ("assistant" if msg.role == "assistant" else "user")
            print(f"{'-' * 60}\n{i:02d} [{nombre}]\n{msg.text}")
            i += 1


if __name__ == "__main__":
    asyncio.run(main())
