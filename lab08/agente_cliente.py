"""
Laboratorio 08 - Agente con Foundry IQ (base de conocimiento gestionada)

Idea central:
-------------
A diferencia de lab07 (donde conectábamos un servidor MCP remoto que ya
existe, o uno propio hecho con FastMCP), aquí el agente y su "herramienta"
de conocimiento se crean y configuran casi por completo desde el portal de
Azure AI Foundry (https://ai.azure.com):

1. En el portal creas un proyecto y un agente (`product-expert-agent`).
2. Conectas ese agente a "Foundry IQ": una base de conocimiento gestionada
   por Azure AI Search que indexa documentos (PDFs de productos, en este
   caso) y responde preguntas usando "agentic retrieval" (búsqueda en
   varios pasos + reranking + síntesis con un LLM).
3. El portal expone esa base de conocimiento al agente como una herramienta
   MCP interna (con prefijo `kb-knowledgebase...`). Con el Foundry Toolkit
   para VS Code, configuras esa herramienta para que pida aprobación antes
   de cada llamada.
4. Este script YA NO define la herramienta ni el modelo a mano: se conecta
   al agente que configuraste en el portal por su nombre y deja que Foundry
   decida cuándo usar Foundry IQ.

Diferencias clave frente al resto del repo (lab06, lab07, S1, chat):
- Usa `azure-ai-projects` (`AIProjectClient`) + `azure-identity`
  (`DefaultAzureCredential`, requiere haber hecho `az login`) en lugar del
  cliente `openai.OpenAI` apuntando directo al endpoint de Azure OpenAI.
- Usa la API de "conversations": la conversación vive del lado del servidor
  (`openai_client.conversations`) y se referencia por su `id`, en vez de
  reenviar la lista completa de mensajes en cada turno.
- Las respuestas se generan con `responses.create(conversation=..., agent_reference=...)`
  en lugar de pasar `model=` y `tools=` explícitamente: el modelo y las
  herramientas ya están fijados en la configuración del agente en el portal.

Flujo de aprobación MCP (igual en espíritu a lab07):
1. Enviamos el mensaje del usuario y pedimos una respuesta.
2. Si el agente quiere usar Foundry IQ, la respuesta trae uno o más bloques
   `mcp_approval_request` en lugar de la respuesta final.
3. Le preguntamos al usuario en la terminal si aprueba cada solicitud.
4. Enviamos las decisiones (`mcp_approval_response`) y pedimos una nueva
   respuesta. Se repite hasta que ya no haya solicitudes pendientes.
"""

import json
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Cargar el .env de esta misma carpeta (lab08/.env), no el de la raíz del
# repo: este laboratorio necesita variables distintas (PROJECT_ENDPOINT,
# AGENT_NAME) que no existen en el .env compartido por los otros labs.
load_dotenv(Path(__file__).parent / ".env")

project_endpoint = os.getenv("PROJECT_ENDPOINT")
agent_name = os.getenv("AGENT_NAME", "product-expert-agent")

if not project_endpoint or project_endpoint == "your_project_endpoint":
    raise SystemExit(
        "Falta configurar PROJECT_ENDPOINT en lab08/.env. Copia el endpoint "
        "de tu proyecto desde la página Home del portal de Azure AI Foundry."
    )


def conectar_agente():
    """Conecta con el proyecto de Foundry, obtiene el agente y crea una
    conversación nueva. Requiere haber hecho `az login` previamente."""

    # exclude_environment_credential / exclude_managed_identity_credential
    # evitan que DefaultAzureCredential intente credenciales que no aplican
    # en un entorno de desarrollo local y acelera la resolución hasta la
    # credencial de Azure CLI (az login).
    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )
    project_client = AIProjectClient(
        credential=credential,
        endpoint=project_endpoint,
    )

    openai_client = project_client.get_openai_client()

    agent = project_client.agents.get(agent_name=agent_name)
    print(f"✅ Conectado al agente: {agent.name} (id: {agent.id})\n")

    conversation = openai_client.conversations.create(items=[])
    print(f"🗂️  Conversación creada (id: {conversation.id})\n")

    return project_client, openai_client, agent, conversation


def pedir_aprobaciones(solicitudes):
    """Muestra cada mcp_approval_request al usuario y devuelve la lista de
    mcp_approval_response con la decisión tomada para cada una."""

    decisiones = []
    for solicitud in solicitudes:
        print(f"🔐 [Aprobación requerida: {solicitud.name}]")
        print(f"   Servidor: {solicitud.server_label}")
        try:
            argumentos = json.loads(solicitud.arguments)
            print(f"   Argumentos: {json.dumps(argumentos, indent=2, ensure_ascii=False)}\n")
        except (TypeError, json.JSONDecodeError):
            print(f"   Argumentos: {solicitud.arguments}\n")

        respuesta = input("¿Aprobar esta acción? (si/no): ").strip().lower()
        aprobado = respuesta in ("si", "sí", "s", "yes", "y")
        print("   → Aprobado, ejecutando...\n" if aprobado else "   → Rechazado.\n")

        decisiones.append(
            {
                "type": "mcp_approval_response",
                "approval_request_id": solicitud.id,
                "approve": aprobado,
            }
        )
    return decisiones


def enviar_mensaje(openai_client, agent, conversation, historial, mensaje_usuario):
    """Envía un mensaje del usuario al agente y resuelve el ciclo de
    aprobaciones MCP hasta obtener una respuesta final."""

    openai_client.conversations.items.create(
        conversation_id=conversation.id,
        items=[{"type": "message", "role": "user", "content": mensaje_usuario}],
    )
    historial.append({"role": "user", "content": mensaje_usuario})

    response = openai_client.responses.create(
        conversation=conversation.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        input="",
    )

    # El agente puede pedir cero, una o varias aprobaciones en el mismo turno
    # (por ejemplo, si consulta Foundry IQ más de una vez). Repetimos hasta
    # que la respuesta ya no traiga solicitudes pendientes.
    while True:
        solicitudes = [
            item for item in (response.output or [])
            if getattr(item, "type", None) == "mcp_approval_request"
        ]
        if not solicitudes:
            break

        decisiones = pedir_aprobaciones(solicitudes)
        openai_client.conversations.items.create(
            conversation_id=conversation.id,
            items=decisiones,
        )
        response = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            input="",
        )

    historial.append({"role": "assistant", "content": response.output_text})
    return response.output_text


def mostrar_historial(historial):
    print("\n" + "=" * 70)
    print("HISTORIAL DE LA CONVERSACIÓN")
    print("=" * 70)
    for turno in historial:
        etiqueta = "🧑 Tú" if turno["role"] == "user" else "🤖 Agente"
        print(f"\n{etiqueta}: {turno['content']}")
    print("=" * 70 + "\n")


def main():
    print("=" * 70)
    print("AGENTE FOUNDRY IQ - product-expert-agent")
    print("=" * 70)
    print("Escribe tu pregunta, 'history' para ver el historial o 'quit' para salir.\n")

    _, openai_client, agent, conversation = conectar_agente()
    historial = []

    while True:
        entrada = input("Tú: ").strip()
        if not entrada:
            continue
        if entrada.lower() == "quit":
            break
        if entrada.lower() == "history":
            mostrar_historial(historial)
            continue

        try:
            respuesta = enviar_mensaje(openai_client, agent, conversation, historial, entrada)
            print(f"\n🤖 Agente: {respuesta}\n")
        except Exception as error:  # errores de red/permmisos del lado de Azure
            print(f"⚠️  Ocurrió un error al hablar con el agente: {error}\n")


if __name__ == "__main__":
    main()
