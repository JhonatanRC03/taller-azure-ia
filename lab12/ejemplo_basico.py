"""
Lab 12 - Ejemplo BÁSICO de backoff exponencial + jitter (con el SDK)

Idea central:
-------------
Cuando Azure OpenAI responde 429 (rate limit exceeded), la peor reacción es
reintentar de inmediato: eso solo agrega más carga a un servicio ya
saturado. Lo correcto es esperar, duplicando el tiempo de espera en cada
fallo (backoff exponencial) y sumándole una variación aleatoria (jitter).

Lo interesante es que el SDK oficial de `openai` **ya implementa esto por
dentro** (ver `openai._base_client._calculate_retry_timeout`): reintenta
automáticamente ante 429, espera con backoff exponencial + jitter, y
respeta el header `retry-after-ms` que manda Azure OpenAI. Por eso, en el
caso más simple, basta con subir `max_retries` (el valor por defecto es
apenas 2) — no hace falta escribir un bucle de reintento a mano.

Para un caso con más control (reintentar solo ante 429 y no ante otros
errores, registrar cada intento, etc.) ver `ejemplo_produccion.py`.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

# El SDK registra internamente "Retrying request to ... in X seconds" cada
# vez que reintenta un 429 (nivel INFO). Activamos ese logger para VER en
# consola el backoff exponencial + jitter en acción, sin escribirlo a mano.
logging.basicConfig(level=logging.INFO, format="⏳ %(message)s")
logging.getLogger("openai").setLevel(logging.INFO)

load_dotenv(Path(__file__).parent.parent / ".env")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = OpenAI(
    base_url=openai_endpoint,
    api_key=auth_key_or_token,
    max_retries=5,  # el SDK reintenta ante 429 con backoff exponencial + jitter
)


def llamar_con_backoff(pregunta: str):
    print(f"→ Enviando solicitud al modelo '{model_deployment}'...")
    try:
        respuesta = client.responses.create(
            model=model_deployment,
            instructions="Eres un asistente útil y conciso.",
            input=pregunta,
        )
    except RateLimitError:
        print("✗ Se agotaron los 5 reintentos automáticos del SDK ante 429.")
        raise

    print("✓ Respuesta recibida correctamente.")
    return respuesta


if __name__ == "__main__":
    respuesta = llamar_con_backoff("Dime un dato curioso sobre el espacio.")
    print(respuesta.output_text)
