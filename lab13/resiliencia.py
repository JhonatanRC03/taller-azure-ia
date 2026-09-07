"""
Lab 13 - Patrones de resiliencia reutilizables: Circuit Breaker.

Ver "Circuit Breaker Pattern" en Azure Architecture Center para la
referencia completa de este patrón. Implementación mínima con tres
estados, pensada para código async:

- **CERRADO**: deja pasar las llamadas con normalidad. Cuenta los fallos
  consecutivos; si llegan al umbral, pasa a ABIERTO.
- **ABIERTO**: rechaza toda llamada de inmediato (sin intentar nada)
  durante `tiempo_abierto_segundos`, para dejar de golpear un servicio
  que ya está fallando. Cuando ese tiempo pasa, pasa a SEMI_ABIERTO.
- **SEMI_ABIERTO**: deja pasar UNA llamada de prueba. Si tiene éxito,
  el circuito asume que el problema se resolvió y vuelve a CERRADO. Si
  falla, vuelve a ABIERTO y reinicia el temporizador.

El Circuit Breaker resuelve un problema distinto al de Retry (lab12):
Retry asume que reintentar eventualmente va a funcionar. Circuit Breaker
asume que, tras varios fallos seguidos, seguir intentando es inútil y
solo desperdicia tiempo/recursos — mejor fallar rápido durante un rato.
"""

import asyncio
import time
from enum import Enum


class CircuitAbiertoError(Exception):
    """Se lanza cuando el circuito está abierto: se rechaza sin intentar la llamada."""


class EstadoCircuito(Enum):
    CERRADO = "cerrado"
    ABIERTO = "abierto"
    SEMI_ABIERTO = "semi_abierto"


class CircuitBreaker:
    def __init__(self, umbral_fallos: int = 3, tiempo_abierto_segundos: float = 30.0):
        self._umbral_fallos = umbral_fallos
        self._tiempo_abierto_segundos = tiempo_abierto_segundos
        self._fallos_consecutivos = 0
        self._estado = EstadoCircuito.CERRADO
        self._abierto_desde: float | None = None
        self._lock = asyncio.Lock()  # varias tareas concurrentes comparten el mismo circuito

    @property
    def estado(self) -> EstadoCircuito:
        return self._estado

    async def ejecutar(self, funcion_async, *args, **kwargs):
        """Ejecuta `funcion_async(*args, **kwargs)` protegida por el circuito."""
        await self._antes_de_llamar()
        try:
            resultado = await funcion_async(*args, **kwargs)
        except Exception:
            await self._despues_de_fallo()
            raise
        else:
            await self._despues_de_exito()
            return resultado

    async def _antes_de_llamar(self):
        async with self._lock:
            if self._estado is EstadoCircuito.ABIERTO:
                if time.monotonic() - self._abierto_desde >= self._tiempo_abierto_segundos:
                    self._estado = EstadoCircuito.SEMI_ABIERTO
                else:
                    raise CircuitAbiertoError("Circuito abierto: se rechaza la llamada sin intentarla.")

    async def _despues_de_exito(self):
        async with self._lock:
            self._fallos_consecutivos = 0
            self._estado = EstadoCircuito.CERRADO

    async def _despues_de_fallo(self):
        async with self._lock:
            self._fallos_consecutivos += 1
            if self._estado is EstadoCircuito.SEMI_ABIERTO or self._fallos_consecutivos >= self._umbral_fallos:
                self._estado = EstadoCircuito.ABIERTO
                self._abierto_desde = time.monotonic()
