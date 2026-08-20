"""
Responses API - Gestión Automática del Contexto
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv("../.env")

# Configuración de Azure OpenAI
openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Cliente de OpenAI
client = OpenAI(
    base_url=openai_endpoint,
    api_key=auth_key_or_token
)

print("=" * 60)
print("RESPONSES API - GESTIÓN AUTOMÁTICA")
print("=" * 60)
print("Escribe 'salir' para terminar\n")

# Variable para mantener el ID de la respuesta anterior
# La API usa esto para mantener el hilo de conversación
last_response_id = None

turno = 1
while True:
    # Solicitar entrada del usuario
    user_input = input(f"[Turno {turno}] Tú: ")
    
    if user_input.lower() in ['salir', 'exit', 'quit']:
        print("\n👋 ¡Hasta luego!")
        break
    
    # La API gestiona automáticamente el historial en el servidor
    # usando el previous_response_id para mantener el contexto
    response = client.responses.create(
        model=model_deployment,
        instructions="Eres un asistente útil. Recuerda la información que el usuario comparta contigo.",
        input=user_input,
        previous_response_id=last_response_id  # Mantiene el hilo de conversación
    )
    
    # Actualizar el ID de la última respuesta para la siguiente iteración
    last_response_id = response.id
    
    # Acceder a la respuesta
    assistant_message = response.output_text
    
    # Mostrar la respuesta
    print(f"🤖 Asistente: {assistant_message}\n")
    print(f"✅ NOTA: La API mantiene el contexto automáticamente usando response_id: {response.id[:8]}...\n")
    
    turno += 1

print("\n" + "=" * 60)
print("FIN DE LA CONVERSACIÓN:")
print("=" * 60)
