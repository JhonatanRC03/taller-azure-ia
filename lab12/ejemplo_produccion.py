"""
Lab 12 - Ejemplo de PRODUCCIÓN para manejar throttling (HTTP 429)

Diferencias respecto a `ejemplo_basico.py`:
--------------------------------------------
1. `ejemplo_basico.py` delega todo el reintento al SDK (`max_retries=5`):
   simple, pero es una caja negra que reintenta ante *cualquier* error
   retryable y no permite loguear/observar cada intento por separado. Aquí
   se usa `tenacity` para tener control explícito: reintentar solo ante
   429, definir la política de espera a medida y registrar cada intento.
2. Respeta el header `retry-after-ms` que Azure OpenAI incluye en la
   respuesta 429 cuando está disponible (el servicio le dice al cliente
   exactamente cuánto esperar). Si no viene ese header, cae de nuevo a
   backoff exponencial + jitter.
3. Reintenta *solo* ante `openai.RateLimitError` (429). Cualquier otro
   error (400, 401, 500, etc.) se propaga de inmediato: reintentar un error
   de autenticación o de validación no lo va a arreglar y solo agrega
   latencia.
4. Deja registro (`logging`) de cada reintento, para poder observar en
   producción cuántos 429 está absorbiendo la política sin que lleguen a
   afectar al usuario final.
5. Deshabilita el retry interno del SDK de `openai` (`max_retries=0`): si
   se deja el retry del SDK activo junto con el de `tenacity`, cada intento
   de `tenacity` podría disparar hasta 2 reintentos adicionales del SDK,
   multiplicando la carga real contra el servicio (justo lo que se busca
   evitar con esta política).
"""

import logging
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("lab12.throttling")

load_dotenv(Path(__file__).parent.parent / ".env")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = OpenAI(
    base_url=openai_endpoint,
    api_key=auth_key_or_token,
    max_retries=0,  # el reintento lo controla tenacity, no el SDK
)


def _segundos_de_retry_after(error: RateLimitError) -> float | None:
    """Lee el header `retry-after-ms` (o `retry-after`) de la respuesta 429."""
    response = getattr(error, "response", None)
    if response is None:
        return None

    retry_after_ms = response.headers.get("retry-after-ms")
    if retry_after_ms is not None:
        return int(retry_after_ms) / 1000

    retry_after = response.headers.get("retry-after")
    if retry_after is not None:
        return float(retry_after)

    return None


def _espera_antes_del_reintento(retry_state):
    """Decide cuánto esperar: prioriza retry-after-ms; si no, backoff+jitter."""
    error = retry_state.outcome.exception()
    espera_sugerida = _segundos_de_retry_after(error)
    if espera_sugerida is not None:
        print(
            f"  ✗ 429 en el intento {retry_state.attempt_number}. El servicio pidió "
            f"esperar {espera_sugerida:.2f}s (header retry-after-ms)."
        )
        logger.warning("429 (intento %s): retry-after-ms=%.2fs", retry_state.attempt_number, espera_sugerida)
        return espera_sugerida

    # Sin header disponible: backoff exponencial con jitter (1s, 2s, 4s, ... + aleatorio)
    espera = min(60, (2 ** retry_state.attempt_number)) * (1 + random.random())
    print(
        f"  ✗ 429 en el intento {retry_state.attempt_number}. Sin retry-after-ms, "
        f"esperando {espera:.2f}s (backoff exponencial + jitter)."
    )
    logger.warning("429 (intento %s): backoff+jitter=%.2fs", retry_state.attempt_number, espera)
    return espera


@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=_espera_antes_del_reintento,
    stop=stop_after_attempt(6),
    reraise=True,  # si se agotan los intentos, propaga el RateLimitError original
)
def _llamar_modelo(pregunta: str):
    print(f"  → Intentando la solicitud al modelo '{model_deployment}'...")
    return client.responses.create(
        model=model_deployment,
        instructions="Eres un asistente útil y conciso.",
        input=pregunta,
    )


def responder(pregunta: str):
    """Punto de entrada público: llama al modelo aplicando la política de reintento."""
    try:
        respuesta = _llamar_modelo(pregunta)
    except RateLimitError:
        print("✗ Se agotaron los 6 intentos permitidos ante 429 (límite de tasa excedido).")
        logger.error("Se agotaron los reintentos ante 429 (límite de tasa excedido).")
        raise

    print("✓ Respuesta recibida correctamente.")
    return respuesta


if __name__ == "__main__":
    respuesta = responder("Dime un dato curioso sobre el espacio.")
    print(respuesta.output_text)
