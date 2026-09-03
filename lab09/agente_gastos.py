"""
Laboratorio 09 - Agente de reclamos de gastos con Microsoft Agent Framework

Idea central:
-------------
A diferencia de lab08 (donde usábamos `azure-ai-projects` + `AIProjectClient`
para conectarnos a un agente YA CREADO en el portal), aquí usamos el nuevo
**Microsoft Agent Framework** (`agent-framework` en PyPI): una librería que
define el agente, sus instrucciones y sus herramientas directamente en
código Python, y luego lo conecta al modelo desplegado en Foundry mediante
`FoundryChatClient`.

Conceptos clave:
- `FoundryChatClient`: el "cliente de chat" que sabe hablar con el modelo
  desplegado en tu proyecto de Foundry (usa PROJECT_ENDPOINT + el nombre del
  deployment). Es equivalente al `openai.OpenAI(base_url=...)` del resto del
  repo, pero integrado con el Agent Framework y con autenticación de Azure.
- `AzureCliCredential`: reutiliza la sesión de `az login` para autenticar
  las llamadas (no se usa una API key como en lab06/S1/chat).
- `@tool(...)`: decorador que convierte una función Python normal en una
  herramienta que el modelo puede decidir invocar. `approval_mode="never_require"`
  significa que se ejecuta automáticamente, sin pedir confirmación (a
  diferencia del flujo de aprobación MCP manual de lab07/lab08).
- `Agent(...)`: agrupa el cliente, el nombre, las instrucciones (system
  prompt) y la lista de `tools` disponibles. Se usa con `async with` porque
  internamente abre/cierra recursos (conexión al modelo, hilo de ejecución).
- `agent.run(mensajes)`: envía los mensajes al agente y devuelve la
  respuesta final, después de que el modelo decida (o no) llamar a las
  herramientas necesarias.
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Referencias a las librerías del Agent Framework
from agent_framework import tool, Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from pydantic import Field
from typing import Annotated

# Cargar el .env de esta misma carpeta (lab09/.env), no el de la raíz del
# repo: este laboratorio necesita PROJECT_ENDPOINT y MODEL_DEPLOYMENT_NAME.
load_dotenv(Path(__file__).parent / ".env")


async def main():
    
    # Cargar el archivo de datos de gastos
    script_dir = Path(__file__).parent
    file_path = script_dir / "data" / "gastos.txt"
    with file_path.open("r", encoding="utf-8") as file:
        datos_gastos = file.read() + "\n"

    # Pedir al usuario qué quiere hacer con los datos
    prompt_usuario = input(
        f"Estos son los datos de gastos en tu archivo:\n\n{datos_gastos}\n"
        "¿Qué te gustaría hacer con ellos?\n\n"
    )

    # Ejecutar el código asíncrono del agente
    await procesar_gastos(prompt_usuario, datos_gastos)


# Función-herramienta que simula el envío de un correo con el reclamo de gastos
@tool(approval_mode="never_require")
def enviar_reclamo(
    para: Annotated[str, Field(description="A quién se envía el correo")],
    asunto: Annotated[str, Field(description="El asunto del correo")],
    cuerpo: Annotated[str, Field(description="El cuerpo del correo en texto")],
):
    # Nota: esta función SIMULA el envío imprimiendo el correo en consola.
    # En una app real, aquí llamarías a un servicio SMTP o similar.
    print("\nPara:", para)
    print("Asunto:", asunto)
    print(cuerpo, "\n")


async def procesar_gastos(prompt, datos_gastos):

    # Crear un cliente de chat de Foundry
    client = FoundryChatClient(
        project_endpoint=os.getenv("PROJECT_ENDPOINT"),
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        credential=AzureCliCredential(),
    )

    # Inicializar un agente con la herramienta y las instrucciones
    async with (
        Agent(
            client=client,
            name="AgenteReclamoGastos",
            instructions="""Eres un asistente de IA para el envío de reclamos de gastos.
                        Cuando el usuario lo solicite, crea un reclamo de gastos y usa la función
                        de la herramienta para enviar un correo a gastos@tallertelescopios.com con
                        el asunto 'Reclamo de gastos' y un cuerpo que contenga los gastos
                        detallados y un total.
                        Luego confirma al usuario que ya lo hiciste. No pidas más información al
                        usuario, usa solo los datos proporcionados para crear el correo.""",
            tools=[enviar_reclamo],
        ) as agente,
    ):
        # Usar el agente para procesar los datos de gastos
        try:
            # Agregar el prompt de entrada a una lista de mensajes a enviar
            mensajes_prompt = [f"{prompt}: {datos_gastos}"]
            # Invocar al agente con los mensajes
            respuesta = await agente.run(mensajes_prompt)
            # Mostrar la respuesta
            print(f"\n# Agente:\n{respuesta}")
        except Exception as e:
            # Algo salió mal
            print(e)


if __name__ == "__main__":
    asyncio.run(main())
