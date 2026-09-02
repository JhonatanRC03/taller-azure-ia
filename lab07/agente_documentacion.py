"""
Laboratorio 07 - Parte 1: Agente conectado a un servidor MCP remoto

Idea central:
-------------
En lugar de escribir nosotros mismos las herramientas, aquí conectamos el agente
a un servidor MCP que YA EXISTE en internet: el servidor de documentación oficial
de Microsoft Learn (https://learn.microsoft.com/api/mcp). Ese servidor expone
herramientas de búsqueda sobre la documentación técnica de Microsoft.

Como en el resto del repositorio (ver lab06/, chat/, S1/), usamos el cliente
estándar de 'openai' apuntando al recurso de Azure OpenAI configurado en el
'.env' de la raíz, en vez de 'azure-ai-projects' + 'az login' (que requeriría
además un 'PROJECT_ENDPOINT' de un proyecto de Azure AI Foundry). El concepto
de "herramienta MCP remota" es el mismo; solo cambia el cliente que la invoca.

Flujo de la Responses API con una tool de tipo "mcp":
1. Le decimos al modelo que tiene disponible una tool de tipo "mcp" (servidor
   remoto). No es una función de Python local: el propio backend del modelo se
   conecta a esa URL y descubre qué herramientas ofrece el servidor.
2. Como configuramos "require_approval": "always", cada vez que el modelo
   quiera invocar una herramienta del servidor MCP, la respuesta trae un
   bloque "mcp_approval_request" en lugar de ejecutarla directamente.
3. Nuestro código revisa esas solicitudes y responde con
   "mcp_approval_response" (approve=True) para autorizar la llamada.
4. El modelo ejecuta la herramienta remota y continúa. Puede pedir varias
   aprobaciones seguidas, así que repetimos el proceso hasta que ya no queden
   solicitudes pendientes.
5. Cuando ya no hay más aprobaciones pendientes, "response.output_text" trae
   la respuesta final en lenguaje natural.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

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
# Definición de la herramienta MCP remota.
# - server_label: etiqueta interna para identificar el servidor.
# - server_url: URL pública del servidor MCP (documentación de Microsoft Learn).
# - require_approval: "always" obliga a aprobar cada llamada antes de
#   ejecutarla (útil para revisar qué está haciendo el agente).
# --------------------------------------------------------------------------
herramienta_mcp_remota = {
    "type": "mcp",
    "server_label": "api-specs",
    "server_url": "https://learn.microsoft.com/api/mcp",
    "require_approval": "always",
}

instrucciones_agente = (
    "Eres un asistente útil que puede usar herramientas MCP para ayudar a los "
    "usuarios. Usa las herramientas MCP disponibles para responder preguntas y "
    "realizar tareas relacionadas con documentación técnica de Microsoft/Azure."
)


def main():
    print("=" * 70)
    print("AGENTE CONECTADO A SERVIDOR MCP REMOTO (Microsoft Learn Docs)")
    print("=" * 70)

    # Historial de mensajes: instrucciones del sistema + pregunta inicial del usuario.
    mensajes = [
        {"role": "developer", "content": instrucciones_agente},
        {
            "role": "user",
            "content": (
                "Dame los comandos de Azure CLI para crear un Azure Container "
                "App con una identidad administrada."
            ),
        },
    ]

    print("\nEnviando la solicitud inicial (puede disparar el uso de la herramienta MCP)...\n")
    response = client.responses.create(
        model=model_deployment,
        input=mensajes,
        tools=[herramienta_mcp_remota],
    )
    mensajes += response.output

    # El agente puede emitir varias llamadas MCP, cada una necesita su propia
    # aprobación, así que repetimos hasta que ya no queden solicitudes pendientes.
    while True:
        solicitudes_aprobacion = [
            item for item in response.output if item.type == "mcp_approval_request"
        ]

        if not solicitudes_aprobacion:
            break

        for solicitud in solicitudes_aprobacion:
            print(f"🔐 Aprobando automáticamente la solicitud MCP: {solicitud.id}")
            mensajes.append(
                {
                    "type": "mcp_approval_response",
                    "approve": True,
                    "approval_request_id": solicitud.id,
                }
            )

        response = client.responses.create(
            model=model_deployment,
            input=mensajes,
            tools=[herramienta_mcp_remota],
        )
        mensajes += response.output

    print(f"🤖 Respuesta del agente:\n{response.output_text}")


if __name__ == "__main__":
    main()
