"""
Chat Completions API - Con Contexto 
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
print("CHAT COMPLETIONS API - CON CONTEXTO")
print("=" * 60)


# Inicializamos el array de mensajes con el prompt del sistema
# Este array CRECE con cada turno de conversación
messages = [
    {"role": "system", "content": "Eres un asistente útil. Recuerda la información que el usuario comparta contigo."}
]

turno = 1
while True:
    # Solicitar entrada del usuario
    user_input = input(f"[Turno {turno}] Tú: ")
    
    if user_input.lower() in ['salir', 'exit', 'quit']:
        print("\n👋 ¡Hasta luego!")
        break
    
    # PASO 1: Agregar el mensaje del usuario al historial
    messages.append({"role": "user", "content": user_input})
    
    # PASO 2: Enviar TODO el historial de mensajes a la API
    # Cada llamada envía TODOS los mensajes anteriores
    response = client.chat.completions.create(
        model=model_deployment,
        messages=messages  # Enviamos el array completo
    )
    
    # PASO 3: Obtener la respuesta del asistente
    assistant_message = response.choices[0].message.content
    
    # PASO 4: Agregar la respuesta del asistente al historial
    messages.append({"role": "assistant", "content": assistant_message})
    
    # Mostrar la respuesta
    print(f"🤖 Asistente: {assistant_message}\n")
    
    # Mostrar estadísticas
    print(f"📊 Total de mensajes en el historial: {len(messages)}")
    print(f"📊 Tokens usados en esta solicitud: {response.usage.total_tokens}")
    
    turno += 1

# RESUMEN FINAL
print("\n" + "=" * 60)
print("RESUMEN DE LA CONVERSACIÓN:")
print("=" * 60)
print(f"Total de turnos: {turno - 1}")
print(f"Total de mensajes en el historial: {len(messages)}")
print("\n⚠️ NOTAS IMPORTANTES:")
print("- El array 'messages' CRECIÓ con cada turno")
print("- Debes gestionar tú mismo el límite de tokens")
print("- Si el historial es muy largo, puedes necesitar truncarlo")
