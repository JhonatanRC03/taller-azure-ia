"""
 Chat Completions API - Uso Básico (Sin Contexto)
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
print("CHAT COMPLETIONS API - SIN CONTEXTO")
print("=" * 60)

# Loop principal
while True:
    # Solicitar entrada del usuario
    user_input = input("Tú: ")
    
    if user_input.lower() in ['salir', 'exit', 'quit']:
        print("\n👋 ¡Hasta luego!")
        break
    
    # IMPORTANTE: Cada llamada solo contiene el mensaje actual
    # NO se mantiene historial de mensajes anteriores
    response = client.chat.completions.create(
        model=model_deployment,
        messages=[
            {"role": "system", "content": "Eres un asistente útil que responde de forma concisa."},
            {"role": "user", "content": user_input}  # Solo el mensaje actual
        ]
    )
    
    # Acceso a la respuesta: completion.choices[0].message.content
    print(f"🤖 Asistente: {response.choices[0].message.content}\n")
    
    # Mostrar estadísticas
    print(f"📊 Tokens usados: {response.usage.total_tokens}")
