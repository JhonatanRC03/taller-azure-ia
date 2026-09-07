"""
Lab 13 - Service layer: orquesta la lógica de negocio y la resiliencia.

Esta capa NO sabe cómo hablar con el modelo (eso es tarea del agent
wrapper de `agente.py`). Su responsabilidad es coordinar:

- **Bulkhead** (aislamiento de recursos, ver "Bulkhead Pattern" en Azure
  Architecture Center): un `asyncio.Semaphore` limita cuántas preguntas
  se procesan al mismo tiempo, para no saturar la cuota del despliegue ni
  agotar recursos locales si llegan muchas solicitudes de golpe.
- **Circuit Breaker** (`resiliencia.py`): si el agente falla varias veces
  seguidas, el circuito se abre y las siguientes solicitudes se rechazan
  de inmediato — sin ni siquiera llamar al modelo — durante un rato.

Esta separación es la que permite, por ejemplo, cambiar el modelo o el
proveedor en `agente.py` sin tocar ninguna regla de negocio ni de
resiliencia definida acá.
"""

import asyncio

from agente import AgenteWrapper
from resiliencia import CircuitAbiertoError, CircuitBreaker


class ServicioOrquestacion:
    def __init__(
        self,
        agente: AgenteWrapper,
        max_llamadas_concurrentes: int = 3,
        umbral_fallos: int = 3,
        tiempo_abierto_segundos: float = 15.0,
    ):
        self._agente = agente
        # Bulkhead: aísla el "presupuesto" de llamadas concurrentes al modelo.
        self._semaforo = asyncio.Semaphore(max_llamadas_concurrentes)
        self._circuito = CircuitBreaker(umbral_fallos, tiempo_abierto_segundos)

    async def responder(self, pregunta: str) -> str:
        async with self._semaforo:  # espera aquí si ya hay demasiadas llamadas en vuelo
            try:
                return await self._circuito.ejecutar(self._agente.preguntar, pregunta)
            except CircuitAbiertoError:
                print(f"  ⛔ circuito abierto: se rechaza '{pregunta[:40]}...' sin llamar al modelo")
                return "El servicio está temporalmente no disponible. Intenta de nuevo en unos segundos."
