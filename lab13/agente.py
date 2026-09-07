"""
Lab 13 - Agent wrapper: la ÚNICA pieza que sabe hablar con el modelo.

Responsabilidad única (separación de responsabilidades): enviar una
pregunta al modelo desplegado en Azure OpenAI y devolver la respuesta de
texto, aplicando dos técnicas que dependen exclusivamente de CÓMO se hace
esa llamada:

- **Timeout** (patrón Timeout): no esperar indefinidamente una respuesta.
  Se configura como `timeout=` al crear el cliente.
- **Retry con backoff exponencial + jitter** (patrón Retry, ver lab12):
  ante un 429 (rate limit), espera un poco más cada vez que reintenta, con
  una variación aleatoria para no sincronizar reintentos con otros
  clientes.

Lo que este archivo NO sabe (y no debe saber): cuántas llamadas van en
paralelo, si conviene llamar o no por fallos recientes del servicio, ni
qué hacer con el resultado. Eso es responsabilidad de `servicio.py`
(capa de orquestación) y `resiliencia.py` (circuit breaker + bulkhead).
"""

import os
import random
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt

load_dotenv(Path(__file__).parent.parent / ".env")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")


class AgenteWrapper:
    """Envuelve al modelo: una sola responsabilidad, hablar con Azure OpenAI."""

    def __init__(self, timeout_segundos: float = 20.0, intentos_maximos: int = 5):
        self._client = AsyncOpenAI(
            base_url=openai_endpoint,
            api_key=auth_key_or_token,
            timeout=timeout_segundos,  # patrón Timeout: no esperar indefinidamente
            max_retries=0,  # el retry lo controla este wrapper, no el SDK
        )
        # Objeto de política de reintento, parametrizado por instancia (se
        # puede llamar como una función: `await self._reintentos(fn, *args)`).
        self._reintentos = AsyncRetrying(
            retry=retry_if_exception_type(RateLimitError),
            wait=self._espera_con_jitter,
            stop=stop_after_attempt(intentos_maximos),
            reraise=True,
        )

    async def preguntar(self, pregunta: str) -> str:
        """Envía `pregunta` al modelo, reintentando ante 429 (backoff + jitter)."""
        respuesta = await self._reintentos(
            self._client.responses.create,
            model=model_deployment,
            instructions="Eres un asistente útil y conciso.",
            input=pregunta,
        )
        return respuesta.output_text

    @staticmethod
    def _espera_con_jitter(retry_state) -> float:
        """Backoff exponencial (tope 30s) + jitter aleatorio (1x a 2x)."""
        return min(30, 2 ** retry_state.attempt_number) * (1 + random.random())
