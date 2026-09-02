"""
Laboratorio 06 - Version "debug" del agente con prints del flujo completo
==========================================================================
Este archivo es una COPIA de agente.py con impresiones (print) agregadas en
cada paso clave, para que puedas ver EXACTAMENTE:

  1. Qué le mandamos al modelo (mensajes + tools).
  2. Qué nos responde el modelo la primera vez (¿texto? ¿function_call?).
  3. Si pidió una función: con qué nombre y qué argumentos (JSON) la pidió.
  4. Qué devuelve la función real de Python al ejecutarla.
  5. Cómo ese resultado se reempaqueta como "function_call_output" y se
     reenvía al modelo.
  6. Qué responde el modelo la segunda vez, ya con el resultado en mano.

No cambia la lógica del agente original: solo agrega prints "de diagnóstico"
marcados con el prefijo [DEBUG] para que sea fácil distinguirlos de la
conversación normal con el agente.
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from funciones import (
    proximo_evento_visible,
    calcular_costo_observacion,
    generar_reporte_observacion,
)

load_dotenv("../.env")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = OpenAI(
    base_url=openai_endpoint,
    api_key=auth_key_or_token,
)

herramienta_evento = {
    "type": "function",
    "name": "proximo_evento_visible",
    "description": "Obtiene el próximo evento astronómico visible desde una ubicación.",
    "parameters": {
        "type": "object",
        "properties": {
            "ubicacion": {
                "type": "string",
                "description": (
                    "Continente donde buscar el próximo evento visible "
                    "(por ejemplo: 'america_del_norte', 'america_del_sur', "
                    "'europa', 'asia', 'africa', 'oceania')."
                ),
            },
        },
        "required": ["ubicacion"],
        "additionalProperties": False,
    },
}

herramienta_costo = {
    "type": "function",
    "name": "calcular_costo_observacion",
    "description": (
        "Calcula el costo de una observación astronómica según el nivel del "
        "telescopio, la cantidad de horas y la prioridad."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "nivel_telescopio": {
                "type": "string",
                "description": "Nivel del telescopio: 'estandar', 'avanzado' o 'premium'.",
            },
            "horas": {
                "type": "number",
                "description": "Número de horas que se usará el telescopio.",
            },
            "prioridad": {
                "type": "string",
                "description": "Prioridad de la observación: 'baja', 'normal' o 'alta'.",
            },
        },
        "required": ["nivel_telescopio", "horas", "prioridad"],
        "additionalProperties": False,
    },
}

herramienta_reporte = {
    "type": "function",
    "name": "generar_reporte_observacion",
    "description": "Genera un reporte en texto que resume una observación astronómica.",
    "parameters": {
        "type": "object",
        "properties": {
            "nombre_evento": {
                "type": "string",
                "description": "Nombre del evento astronómico observado.",
            },
            "ubicacion": {
                "type": "string",
                "description": "Ubicación (continente) desde donde se observó.",
            },
            "nivel_telescopio": {
                "type": "string",
                "description": "Nivel del telescopio usado: 'estandar', 'avanzado' o 'premium'.",
            },
            "horas": {
                "type": "number",
                "description": "Cantidad de horas que se usó el telescopio.",
            },
            "prioridad": {
                "type": "string",
                "description": "Prioridad de la observación: 'baja', 'normal' o 'alta'.",
            },
            "nombre_observador": {
                "type": "string",
                "description": "Nombre de la persona o institución que realizó la observación.",
            },
        },
        "required": [
            "nombre_evento",
            "ubicacion",
            "nivel_telescopio",
            "horas",
            "prioridad",
            "nombre_observador",
        ],
        "additionalProperties": False,
    },
}

function_tools = [herramienta_evento, herramienta_costo, herramienta_reporte]

instrucciones_agente = (
    "Eres un asistente de observaciones astronómicas. Ayudas a las personas a "
    "encontrar información sobre eventos astronómicos y a calcular el costo del "
    "alquiler de telescopios. Usa las herramientas disponibles cuando las necesites."
)


def linea(titulo: str = "") -> None:
    """Imprime un separador visual para que cada paso del flujo se distinga fácil."""
    if titulo:
        print(f"\n[DEBUG] ----- {titulo} -----")
    else:
        print("[DEBUG] " + "-" * 60)


def ejecutar_funcion(nombre: str, argumentos: dict) -> str:
    """Ejecuta en Python la función real que corresponde al nombre pedido por el modelo."""
    if nombre == "proximo_evento_visible":
        return proximo_evento_visible(**argumentos)
    if nombre == "calcular_costo_observacion":
        return calcular_costo_observacion(**argumentos)
    if nombre == "generar_reporte_observacion":
        return generar_reporte_observacion(**argumentos)
    return json.dumps({"error": f"Función desconocida: {nombre}"}, ensure_ascii=False)


def main():
    print("=" * 70)
    print("AGENTE DE OBSERVACIONES ASTRONÓMICAS (modo DEBUG - ver flujo completo)")
    print("=" * 70)
    print("Escribe 'salir' para terminar\n")

    mensajes = [{"role": "developer", "content": instrucciones_agente}]

    while True:
        prompt = input("Tú: ")
        if prompt.lower() in ("salir", "exit", "quit"):
            print("\n👋 ¡Hasta luego!")
            break

        mensajes.append({"role": "user", "content": prompt})

        # --------------------------------------------------------------
        # PASO 1: qué le enviamos al modelo (el historial completo + tools)
        # --------------------------------------------------------------
        linea("PASO 1: enviamos al modelo (input + tools)")
        print(f"[DEBUG] Mensaje nuevo del usuario: {prompt!r}")
        print(f"[DEBUG] Cantidad de mensajes en el historial que se envían: {len(mensajes)}")
        print("[DEBUG] Herramientas disponibles: "
              f"{[t['name'] for t in function_tools]}")

        response = client.responses.create(
            model=model_deployment,
            input=mensajes,
            tools=function_tools,
        )

        if response.status == "failed":
            print(f"⚠️  La respuesta falló: {response.error}")
            continue

        # --------------------------------------------------------------
        # PASO 2: qué contestó el modelo la PRIMERA vez (crudo)
        # --------------------------------------------------------------
        linea("PASO 2: primera respuesta cruda del modelo (response.output)")
        for i, item in enumerate(response.output):
            print(f"[DEBUG] output[{i}] -> type={item.type!r}")
            if item.type == "function_call":
                print(f"[DEBUG]    nombre de la función pedida: {item.name}")
                print(f"[DEBUG]    argumentos (JSON string):    {item.arguments}")
                print(f"[DEBUG]    call_id:                     {item.call_id}")
            elif item.type == "message":
                print(f"[DEBUG]    texto: {getattr(item, 'content', item)}")

        mensajes += response.output

        # --------------------------------------------------------------
        # PASO 3: ejecutamos cada function_call que haya pedido el modelo
        # --------------------------------------------------------------
        hubo_llamada_funcion = False
        for item in response.output:
            if item.type == "function_call":
                hubo_llamada_funcion = True

                linea(f"PASO 3: ejecutando función '{item.name}'")
                argumentos = json.loads(item.arguments)
                print(f"[DEBUG] Argumentos ya convertidos a dict: {argumentos}")

                resultado = ejecutar_funcion(item.name, argumentos)
                print(f"[DEBUG] Resultado devuelto por la función (JSON string):")
                print(f"[DEBUG]   {resultado}")

                # Este es el paquete que se reenvía al modelo como "salida de función"
                salida_funcion = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": resultado,
                }
                print(f"[DEBUG] Esto se agrega al historial para el modelo: {salida_funcion}")
                mensajes.append(salida_funcion)

        # --------------------------------------------------------------
        # PASO 4: si hubo funciones, le devolvemos los resultados al modelo
        # --------------------------------------------------------------
        if hubo_llamada_funcion:
            linea("PASO 4: reenviamos los resultados de función al modelo")
            print(f"[DEBUG] Cantidad de mensajes que se reenvían: {len(mensajes)}")

            response = client.responses.create(
                model=model_deployment,
                input=mensajes,
                tools=function_tools,
            )
            mensajes += response.output

            linea("PASO 4b: segunda respuesta cruda del modelo (ya con datos)")
            for i, item in enumerate(response.output):
                print(f"[DEBUG] output[{i}] -> type={item.type!r}")
        else:
            linea("El modelo respondió directo, sin necesitar ninguna función")

        # --------------------------------------------------------------
        # PASO 5: respuesta final en texto que ve el usuario
        # --------------------------------------------------------------
        linea("PASO 5: respuesta final (response.output_text)")
        print(f"\n🤖 AGENTE: {response.output_text}\n")


if __name__ == "__main__":
    main()
