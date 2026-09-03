"""
Lab10 - Despliegue HOSTED (Foundry Hosted Agent) de un agente con Agent Framework

Idea central:
-------------
En un Hosted Agent, tu código NO se ejecuta "una vez y termina" (como en
../autoalojado/agente_autoalojado.py). En vez de eso, expones el `Agent`
detrás de un SERVIDOR HTTP que habla el protocolo que Foundry espera
("Responses", compatible con la API de respuestas de OpenAI). Azure
Developer CLI (`azd ai agent`) sabe cómo:

1. Correr ese servidor localmente para que lo pruebes (`azd ai agent run`).
2. Empaquetarlo en un contenedor y publicarlo en tu proyecto de Foundry
   como una entidad de agente real, versionada (`azd deploy`).

`agent_framework.devui.serve(...)` es justo la pieza que arma ese servidor
HTTP a partir de tu `Agent`. Es la MISMA función que usa `azd ai agent run`
por debajo cuando corres un agente Python localmente antes de desplegarlo.

Diferencias clave frente a ../autoalojado/agente_autoalojado.py:
- Aquí NO llamamos a `agente.run(...)` directamente en `main()`. En vez de
  eso, le entregamos el agente a `serve(...)`, que deja un servidor HTTP
  escuchando en un puerto, esperando peticiones (una por cada turno de
  conversación).
- El archivo se llama `main.py` porque ese es el nombre de entry point que
  espera `azd ai agent init --entry-point main.py`.
- En un proyecto real escalado con `azd`, este archivo vive dentro de
  `src/<nombre-del-agente>/`, junto a un `azure.yaml` en la raíz del
  proyecto que declara el servicio (ver azure.yaml.ejemplo en esta carpeta).

Cómo probarlo LOCALMENTE (sin desplegar nada a Azure todavía):
1. Completa el .env de esta carpeta con tu PROJECT_ENDPOINT y
   MODEL_DEPLOYMENT_NAME (los mismos de lab09).
2. Instala las dependencias: agent-framework-foundry y agent-framework-devui
   (ya están en el requirements.txt de la raíz del repo).
3. az login (para AzureCliCredential).
4. Ejecuta: python main.py
5. Abre http://127.0.0.1:8080 en el navegador: verás el "Agent Inspector"
   (una UI de prueba), o puedes mandar peticiones HTTP directas al
   endpoint de "responses" que expone el servidor.

Cómo se PUBLICA de verdad como Hosted Agent (con la extensión/azd):
- Con `azd`: `azd ai agent init` (para scaffoldear el proyecto igual que
  esta carpeta), luego `azd provision` (crea/usa el proyecto de Foundry) y
  `azd deploy` (construye la imagen y la registra como una nueva versión
  del agente dentro de tu proyecto de Foundry). Después queda invocable de
  forma remota, versionado, con logs y evaluación integrados en el portal.
- Ese flujo completo (con recursos reales de Azure) NO se ejecuta en este
  laboratorio: aquí solo ves la FORMA del código y el arranque local.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from agent_framework import tool, Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework.devui import serve
from azure.identity import AzureCliCredential
from pydantic import Field
from typing import Annotated

load_dotenv(Path(__file__).parent / ".env")


# Misma herramienta de ejemplo que en la versión autoalojada, para que la
# comparación sea justa: lo único que cambia es CÓMO se expone el agente.
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


def crear_agente() -> Agent:
    client = FoundryChatClient(
        project_endpoint=os.getenv("PROJECT_ENDPOINT"),
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        credential=AzureCliCredential(),
    )

    return Agent(
        client=client,
        name="AgenteInventarioHosted",
        instructions="""Eres un asistente de la tienda de telescopios.
                    Usa la herramienta disponible para responder preguntas sobre
                    disponibilidad de productos. Sé breve y directo.""",
        tools=[consultar_disponibilidad],
    )


if __name__ == "__main__":
    agente = crear_agente()

    # `serve(...)` NO corre el agente una sola vez: deja un servidor HTTP
    # vivo que Foundry (o `azd ai agent run` localmente) puede invocar una
    # y otra vez, un turno de conversación por petición.
    # auth_enabled=False: solo para pruebas locales en 127.0.0.1 (en un
    # Hosted Agent real desplegado, Foundry gestiona la autenticación).
    serve(entities=[agente], port=8080, host="127.0.0.1", auto_open=False, auth_enabled=False)
