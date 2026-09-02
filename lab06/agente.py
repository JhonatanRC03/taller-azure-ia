"""
Laboratorio 06 - Agente de IA con funciones personalizadas (custom function tools)
====================================================================================
Este script recrea el laboratorio de Microsoft Learn "Use a custom function in an
AI agent", adaptado al estilo de este proyecto: en lugar de usar el paquete
'azure-ai-projects' (que requiere un proyecto de Foundry + 'az login'), usamos el
cliente estándar de 'openai' apuntando al recurso de Azure OpenAI configurado en
el archivo .env de la raíz (AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY /
AZURE_OPENAI_DEPLOYMENT), igual que en el resto de scripts del repo (chat/, S1/).

Idea central del laboratorio:
1. Definimos "function tools": funciones de Python + un esquema JSON que describe
   su nombre, descripción y parámetros. El modelo usa la descripción para decidir
   CUÁNDO conviene llamarlas, y el esquema para saber CÓMO llamarlas (qué
   argumentos enviar).
2. Enviamos el mensaje del usuario junto con la lista de "tools" disponibles.
3. Si el modelo decide que necesita una función, la respuesta incluye un
   "function_call" con el nombre de la función y los argumentos en JSON.
4. Nuestro código ejecuta esa función real en Python (aquí sí se ejecuta código,
   el modelo solo "pide" que se ejecute) y le devuelve el resultado como
   "function_call_output".
5. Con ese resultado, el modelo genera la respuesta final en lenguaje natural.
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

# Cargar variables de entorno desde el .env que está en la raíz del proyecto
load_dotenv("../.env")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Cliente que apunta al recurso de Azure OpenAI ya configurado
client = OpenAI(
    base_url=openai_endpoint,
    api_key=auth_key_or_token,
)

# --------------------------------------------------------------------------
# Definición de las "function tools" que el agente puede usar.
# El "type": "function" indica que es una herramienta de tipo función.
# "parameters" es un JSON Schema: describe qué argumentos espera la función
# y de qué tipo son. El modelo se apoya en esto para construir la llamada.
# --------------------------------------------------------------------------

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

# Lista de herramientas que se envía al modelo en cada llamada
function_tools = [herramienta_evento, herramienta_costo, herramienta_reporte]

# Instrucciones de sistema (rol "developer") para el agente
instrucciones_agente = (
    "Eres un asistente de observaciones astronómicas. Ayudas a las personas a "
    "encontrar información sobre eventos astronómicos y a calcular el costo del "
    "alquiler de telescopios. Usa las herramientas disponibles cuando las necesites."
)


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
    print("AGENTE DE OBSERVACIONES ASTRONÓMICAS (function tools personalizadas)")
    print("=" * 70)
    print("Escribe 'salir' para terminar\n")

    # Mantenemos el historial completo en memoria y lo reenviamos en cada
    # turno junto con las salidas de las funciones que se vayan ejecutando.
    mensajes = [{"role": "developer", "content": instrucciones_agente}]

    while True:
        prompt = input("Tú: ")
        if prompt.lower() in ("salir", "exit", "quit"):
            print("\n👋 ¡Hasta luego!")
            break

        mensajes.append({"role": "user", "content": prompt})

        # 1) Primera llamada al modelo: puede responder directamente o pedir
        #    que se ejecute una o varias funciones (function_call).
        response = client.responses.create(
            model=model_deployment,
            input=mensajes,
            tools=function_tools,
        )

        if response.status == "failed":
            print(f"⚠️  La respuesta falló: {response.error}")
            continue

        # Agregamos la salida del modelo (texto y/o function_call) al historial
        mensajes += response.output

        # 2) Revisamos si el modelo pidió ejecutar alguna función
        hubo_llamada_funcion = False
        for item in response.output:
            if item.type == "function_call":
                hubo_llamada_funcion = True
                argumentos = json.loads(item.arguments)
                resultado = ejecutar_funcion(item.name, argumentos)

                # Devolvemos el resultado de la función como parte del historial,
                # asociado al mismo call_id para que el modelo sepa a qué llamada corresponde.
                mensajes.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": resultado,
                })

        # 3) Si hubo llamadas a funciones, le pedimos al modelo una respuesta
        #    final usando los resultados obtenidos.
        if hubo_llamada_funcion:
            response = client.responses.create(
                model=model_deployment,
                input=mensajes,
                tools=function_tools,
            )
            mensajes += response.output

        print(f"\n🤖 AGENTE: {response.output_text}\n")


if __name__ == "__main__":
    main()
