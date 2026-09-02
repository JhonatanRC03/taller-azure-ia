"""
Laboratorio 07 - Parte 2b: Cliente MCP + Agente de inventario
===============================================================

¿Qué hace este script?
-----------------------
Este es el "puente" entre el servidor MCP personalizado ('servidor_mcp.py') y
el modelo de IA:

1. Arranca 'servidor_mcp.py' como subproceso y abre un canal de comunicación
   por stdio (entrada/salida estándar) usando el protocolo MCP.
2. Le pregunta al servidor qué herramientas tiene disponibles
   ("consultar_inventario", "consultar_ventas_semanales").
3. Convierte cada una de esas herramientas MCP en una "function tool" que el
   modelo puede pedir invocar (igual que en lab06/agente.py, pero aquí las
   funciones no están escritas a mano: se descubren dinámicamente).
4. Cuando el modelo pide ejecutar una herramienta, este script reenvía esa
   petición al servidor MCP real (session.call_tool), obtiene el resultado y
   se lo devuelve al modelo para que redacte la respuesta final.

Como en el resto del repositorio, usamos el cliente estándar de 'openai'
apuntando al recurso de Azure OpenAI configurado en el '.env' de la raíz
(en vez de 'azure-ai-projects' + 'az login').
"""

import asyncio
import json
import os
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

# Cargar variables de entorno desde el .env que está en la raíz del proyecto
load_dotenv("../.env")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = OpenAI(
    base_url=openai_endpoint,
    api_key=auth_key_or_token,
)

# Instrucciones de sistema (rol "developer") para el agente de inventario.
instrucciones_agente = (
    "Eres un asistente de inventario de una tienda de telescopios. "
    "Reglas generales:\n"
    "- Recomienda reabastecer (restock) si el inventario de un producto es "
    "menor a 10 unidades y sus ventas semanales son mayores a 15.\n"
    "- Recomienda liquidar (clearance) si el inventario es mayor a 20 unidades "
    "y las ventas semanales son menores a 5."
)


async def conectar_al_servidor(exit_stack: AsyncExitStack) -> ClientSession:
    """Arranca servidor_mcp.py como subproceso y abre una sesión MCP sobre stdio."""
    parametros_servidor = StdioServerParameters(
        command="python",
        args=["servidor_mcp.py"],
        env=None,
    )

    # Iniciar el servidor MCP como subproceso y obtener los streams de lectura/escritura
    transporte_stdio = await exit_stack.enter_async_context(stdio_client(parametros_servidor))
    stdio, write = transporte_stdio

    # Crear la sesión de cliente MCP sobre esos streams e inicializarla
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()

    # Listar las herramientas disponibles para confirmar que la conexión funcionó
    respuesta = await session.list_tools()
    herramientas = respuesta.tools
    print("Conectado al servidor MCP. Herramientas disponibles:", [h.name for h in herramientas])

    return session


def construir_function_tool(tool) -> dict:
    """Convierte la descripción de una tool MCP al formato 'function tool' de la Responses API."""
    # El nombre del atributo del esquema cambia según la versión del SDK de mcp
    # ('input_schema' en versiones nuevas, 'inputSchema' en versiones antiguas).
    parametros = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description or "",
        "parameters": parametros,
    }


async def bucle_conversacion(session: ClientSession):
    respuesta_tools = await session.list_tools()
    herramientas_mcp = respuesta_tools.tools

    # Envolver cada tool MCP en una función async de Python invocable localmente.
    def crear_funcion(nombre_tool: str):
        async def funcion(**kwargs):
            return await session.call_tool(nombre_tool, kwargs)

        funcion.__name__ = nombre_tool
        return funcion

    # Diccionario nombre_de_la_tool -> función async que la ejecuta de verdad
    funciones = {tool.name: crear_funcion(tool.name) for tool in herramientas_mcp}

    # Tools en el formato que espera la Responses API
    function_tools = [construir_function_tool(tool) for tool in herramientas_mcp]

    mensajes = [{"role": "developer", "content": instrucciones_agente}]

    print("\nEscribe 'salir' para terminar.\n")
    while True:
        prompt = input("Tú: ").strip()
        if prompt.lower() in ("salir", "exit", "quit"):
            print("\n👋 ¡Hasta luego!")
            break

        mensajes.append({"role": "user", "content": prompt})

        response = client.responses.create(
            model=model_deployment,
            input=mensajes,
            tools=function_tools,
        )

        if response.status == "failed":
            print(f"⚠️ La respuesta falló: {response.error}")
            continue

        # Agregamos la salida del modelo (texto y/o function_call) al historial
        mensajes += response.output

        # El modelo puede necesitar varias rondas de llamadas a herramientas
        # (por ejemplo: primero consulta inventario y luego ventas), así que
        # repetimos mientras sigan apareciendo function_call en la respuesta.
        llamadas_pendientes = [item for item in response.output if item.type == "function_call"]

        while llamadas_pendientes:
            for item in llamadas_pendientes:
                argumentos = json.loads(item.arguments or "{}")
                funcion = funciones.get(item.name)
                resultado = await funcion(**argumentos)
                texto_resultado = resultado.content[0].text if resultado.content else "{}"

                # Devolvemos el resultado de la herramienta, asociado al mismo
                # call_id, para que el modelo sepa a qué llamada corresponde.
                mensajes.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": texto_resultado,
                    }
                )

            response = client.responses.create(
                model=model_deployment,
                input=mensajes,
                tools=function_tools,
            )
            mensajes += response.output
            llamadas_pendientes = [item for item in response.output if item.type == "function_call"]

        print(f"🤖 Agente: {response.output_text}\n")


async def main():
    exit_stack = AsyncExitStack()
    try:
        session = await conectar_al_servidor(exit_stack)
        await bucle_conversacion(session)
    finally:
        await exit_stack.aclose()


if __name__ == "__main__":
    print("=" * 70)
    print("CLIENTE MCP + AGENTE DE INVENTARIO DE TELESCOPIOS")
    print("=" * 70)
    asyncio.run(main())
