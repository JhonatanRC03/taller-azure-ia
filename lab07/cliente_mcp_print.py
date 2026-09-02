"""
Laboratorio 07 - Version "debug" del cliente MCP con prints del flujo completo
=================================================================================
Este archivo es una COPIA de cliente_mcp.py con impresiones (print) agregadas en
cada paso clave, para que puedas ver EXACTAMENTE:

  0. Cómo se arranca el servidor MCP y qué responde cuando le preguntamos
     "qué herramientas tienes" (session.list_tools()).
  1. Cómo se construye, herramienta por herramienta, el "function tool" que
     entiende la Responses API (a partir de lo que dijo el servidor, sin que
     nosotros hayamos escrito ese JSON a mano).
  2. Qué le mandamos al modelo (mensajes + tools).
  3. Qué nos responde el modelo la primera vez (¿texto? ¿function_call?).
  4. Si pidió una función: con qué nombre y qué argumentos la pidió, y cómo
     ese nombre se traduce en una llamada real al servidor MCP
     (session.call_tool) en vez de a una función de Python local.
  5. Qué devuelve el servidor MCP al ejecutar la herramienta.
  6. Cómo ese resultado se reempaqueta como "function_call_output" y se
     reenvía al modelo.
  7. Qué responde el modelo ya con el resultado en mano.

No cambia la lógica de cliente_mcp.py: solo agrega prints "de diagnóstico"
marcados con el prefijo [DEBUG] para que sea fácil distinguirlos de la
conversación normal con el agente.
"""

import asyncio
import json
import os
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

load_dotenv("../.env")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = OpenAI(
    base_url=openai_endpoint,
    api_key=auth_key_or_token,
)

instrucciones_agente = (
    "Eres un asistente de inventario de una tienda de telescopios. "
    "Reglas generales:\n"
    "- Recomienda reabastecer (restock) si el inventario de un producto es "
    "menor a 10 unidades y sus ventas semanales son mayores a 15.\n"
    "- Recomienda liquidar (clearance) si el inventario es mayor a 20 unidades "
    "y las ventas semanales son menores a 5."
)


def linea(titulo: str = "") -> None:
    """Imprime un separador visual para que cada paso del flujo se distinga fácil."""
    if titulo:
        print(f"\n[DEBUG] ----- {titulo} -----")
    else:
        print("[DEBUG] " + "-" * 60)


async def conectar_al_servidor(exit_stack: AsyncExitStack) -> ClientSession:
    """Arranca servidor_mcp.py como subproceso y abre una sesión MCP sobre stdio."""
    linea("PASO 0a: arrancando servidor_mcp.py como subproceso (stdio)")
    parametros_servidor = StdioServerParameters(
        command="python",
        args=["servidor_mcp.py"],
        env=None,
    )
    print(f"[DEBUG] Comando que se ejecuta: {parametros_servidor.command} {parametros_servidor.args}")

    transporte_stdio = await exit_stack.enter_async_context(stdio_client(parametros_servidor))
    stdio, write = transporte_stdio
    print("[DEBUG] Streams de lectura/escritura (stdio) listos.")

    linea("PASO 0b: creando la sesión MCP e inicializando el protocolo")
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()
    print("[DEBUG] session.initialize() completado: el handshake MCP terminó bien.")

    linea("PASO 0c: preguntándole al servidor qué herramientas tiene (list_tools)")
    respuesta = await session.list_tools()
    herramientas = respuesta.tools
    for h in herramientas:
        print(f"[DEBUG] Tool descubierta -> nombre={h.name!r}, descripción={h.description!r}")
    print(f"[DEBUG] Total de herramientas descubiertas: {len(herramientas)}")

    return session


def construir_function_tool(tool) -> dict:
    """Convierte la descripción de una tool MCP al formato 'function tool' de la Responses API."""
    parametros = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    function_tool = {
        "type": "function",
        "name": tool.name,
        "description": tool.description or "",
        "parameters": parametros,
    }
    print(f"[DEBUG] Tool MCP {tool.name!r} -> function tool construido dinámicamente:")
    print(f"[DEBUG]   {json.dumps(function_tool, ensure_ascii=False)}")
    return function_tool


async def bucle_conversacion(session: ClientSession):
    respuesta_tools = await session.list_tools()
    herramientas_mcp = respuesta_tools.tools

    linea("PASO 1: construyendo dinámicamente las function tools y el dispatcher")

    def crear_funcion(nombre_tool: str):
        async def funcion(**kwargs):
            print(f"[DEBUG] -> Reenviando al servidor MCP: call_tool({nombre_tool!r}, {kwargs})")
            return await session.call_tool(nombre_tool, kwargs)

        funcion.__name__ = nombre_tool
        return funcion

    # Diccionario nombre_de_la_tool -> función async que la ejecuta de verdad.
    # Nadie escribió "if nombre == ...": se arma solo a partir de lo descubierto.
    funciones = {tool.name: crear_funcion(tool.name) for tool in herramientas_mcp}
    print(f"[DEBUG] Dispatcher construido para: {list(funciones.keys())}")

    function_tools = [construir_function_tool(tool) for tool in herramientas_mcp]

    mensajes = [{"role": "developer", "content": instrucciones_agente}]

    print("\nEscribe 'salir' para terminar.\n")
    while True:
        prompt = input("Tú: ").strip()
        if prompt.lower() in ("salir", "exit", "quit"):
            print("\n👋 ¡Hasta luego!")
            break

        mensajes.append({"role": "user", "content": prompt})

        # --------------------------------------------------------------
        # PASO 2: qué le enviamos al modelo (el historial completo + tools)
        # --------------------------------------------------------------
        linea("PASO 2: enviamos al modelo (input + tools)")
        print(f"[DEBUG] Mensaje nuevo del usuario: {prompt!r}")
        print(f"[DEBUG] Cantidad de mensajes en el historial que se envían: {len(mensajes)}")
        print(f"[DEBUG] Herramientas disponibles: {[t['name'] for t in function_tools]}")

        response = client.responses.create(
            model=model_deployment,
            input=mensajes,
            tools=function_tools,
        )

        if response.status == "failed":
            print(f"⚠️ La respuesta falló: {response.error}")
            continue

        # --------------------------------------------------------------
        # PASO 3: qué contestó el modelo la PRIMERA vez (crudo)
        # --------------------------------------------------------------
        linea("PASO 3: primera respuesta cruda del modelo (response.output)")
        for i, item in enumerate(response.output):
            print(f"[DEBUG] output[{i}] -> type={item.type!r}")
            if item.type == "function_call":
                print(f"[DEBUG]    nombre de la función pedida: {item.name}")
                print(f"[DEBUG]    argumentos (JSON string):    {item.arguments}")
                print(f"[DEBUG]    call_id:                     {item.call_id}")

        mensajes += response.output

        llamadas_pendientes = [item for item in response.output if item.type == "function_call"]

        ronda = 1
        while llamadas_pendientes:
            linea(f"PASO 4 (ronda {ronda}): ejecutando {len(llamadas_pendientes)} llamada(s) vía MCP")
            for item in llamadas_pendientes:
                argumentos = json.loads(item.arguments or "{}")
                print(f"[DEBUG] Argumentos ya convertidos a dict: {argumentos}")

                funcion = funciones.get(item.name)
                resultado = await funcion(**argumentos)
                texto_resultado = resultado.content[0].text if resultado.content else "{}"
                print(f"[DEBUG] Resultado devuelto por el servidor MCP (JSON string):")
                print(f"[DEBUG]   {texto_resultado}")

                salida_funcion = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": texto_resultado,
                }
                print(f"[DEBUG] Esto se agrega al historial para el modelo: {salida_funcion}")
                mensajes.append(salida_funcion)

            linea(f"PASO 4b (ronda {ronda}): reenviamos los resultados al modelo")
            print(f"[DEBUG] Cantidad de mensajes que se reenvían: {len(mensajes)}")

            response = client.responses.create(
                model=model_deployment,
                input=mensajes,
                tools=function_tools,
            )
            mensajes += response.output

            linea(f"PASO 4c (ronda {ronda}): nueva respuesta cruda del modelo")
            for i, item in enumerate(response.output):
                print(f"[DEBUG] output[{i}] -> type={item.type!r}")

            llamadas_pendientes = [item for item in response.output if item.type == "function_call"]
            ronda += 1

        if ronda == 1:
            linea("El modelo respondió directo, sin necesitar ninguna herramienta")

        # --------------------------------------------------------------
        # PASO 5: respuesta final en texto que ve el usuario
        # --------------------------------------------------------------
        linea("PASO 5: respuesta final (response.output_text)")
        print(f"\n🤖 Agente: {response.output_text}\n")


async def main():
    exit_stack = AsyncExitStack()
    try:
        session = await conectar_al_servidor(exit_stack)
        await bucle_conversacion(session)
    finally:
        await exit_stack.aclose()


if __name__ == "__main__":
    print("=" * 70)
    print("CLIENTE MCP + AGENTE DE INVENTARIO (modo DEBUG - ver flujo completo)")
    print("=" * 70)
    asyncio.run(main())
