"""
Lab10 - Despliegue AUTOALOJADO (self-hosted) de un agente con Agent Framework

Idea central:
-------------
Este script es EXACTAMENTE el mismo tipo de código que ya viste en lab09
(agente_gastos.py): un programa Python normal que crea un `Agent` con
`agent_framework` y lo corre localmente con `asyncio.run(...)`.

La diferencia no está en el código del agente, sino en QUÉ HACES DESPUÉS
para "publicarlo":

- Aquí, "desplegar" significa simplemente ejecutar este archivo en algún
  lugar que no sea tu laptop: un contenedor (ver Dockerfile en esta misma
  carpeta), una VM, un Azure Container App, un App Service, una Azure
  Function, etc.
- Para Foundry, esto es invisible: Foundry solo ve llamadas al modelo
  (como cualquier llamada de API). NO aparece nada en "Build > Agents" del
  portal, no hay versiones, no hay evaluación ni observabilidad integradas.
- Tú eres responsable de todo el ciclo de vida: build de la imagen, push a
  un registro de contenedores, definir el hosting, logs, reinicios, etc.

Este es el enfoque más simple y rápido para prototipos o scripts internos,
pero NO es el que se usa a diario en producción con Foundry (para eso ver
../hosted/main.py).
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from agent_framework import tool, Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from pydantic import Field
from typing import Annotated

load_dotenv(Path(__file__).parent / ".env")


# Herramienta muy simple: consulta un "inventario" fijo en memoria.
@tool(approval_mode="never_require")
def consultar_disponibilidad(
    producto: Annotated[str, Field(description="Nombre del producto a consultar")],
) -> str:
    inventario = {
        "telescopio refractor 70mm": 5,
        "telescopio reflector 130mm": 2,
        "montura ecuatorial": 8,
    }
    unidades = inventario.get(producto.lower())
    if unidades is None:
        return f"No tengo información de '{producto}' en el inventario."
    return f"Hay {unidades} unidades disponibles de '{producto}'."


async def main():
    # Cliente de chat de Foundry (idéntico al de lab09)
    client = FoundryChatClient(
        project_endpoint=os.getenv("PROJECT_ENDPOINT"),
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        credential=AzureCliCredential(),
    )

    async with (
        Agent(
            client=client,
            name="AgenteInventarioAutoalojado",
            instructions="""Eres un asistente de la tienda de telescopios.
                        Usa la herramienta disponible para responder preguntas sobre
                        disponibilidad de productos. Sé breve y directo.""",
            tools=[consultar_disponibilidad],
        ) as agente,
    ):
        pregunta = "¿Cuántos telescopios reflector 130mm hay disponibles?"
        print(f"Usuario: {pregunta}\n")
        respuesta = await agente.run([pregunta])
        print(f"Agente: {respuesta}")


if __name__ == "__main__":
    # Este es TODO el "runtime": solo un proceso de Python que corre una vez y termina.
    # Para desplegarlo, empaquetas este proceso (ver Dockerfile) y lo corres donde quieras.
    asyncio.run(main())
