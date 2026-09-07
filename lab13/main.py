"""
Lab 13 - Demo: agentes en producción con capas separadas y resiliencia.

Corre dos demostraciones:

1) `demo_bulkhead`: varias preguntas reales en paralelo (`asyncio.gather`)
   contra el modelo, para ver el Bulkhead (semáforo) limitando cuántas
   llamadas concurrentes llegan al modelo a la vez.
2) `demo_circuit_breaker`: una simulación con una función que siempre
   falla (sin llamar al modelo real, para no gastar cuota), para ver el
   Circuit Breaker abrirse, rechazar llamadas sin intentar nada, y luego
   pasar a semi-abierto para probar si el servicio "se recuperó".
"""

import asyncio

from agente import AgenteWrapper
from resiliencia import CircuitAbiertoError, CircuitBreaker
from servicio import ServicioOrquestacion


async def demo_bulkhead():
    print("=" * 70)
    print("DEMO 1: Bulkhead - control de concurrencia con preguntas reales")
    print("=" * 70)

    agente = AgenteWrapper()
    servicio = ServicioOrquestacion(agente, max_llamadas_concurrentes=2)

    preguntas = [
        "Dime un dato curioso sobre Marte, en una oración.",
        "Dime un dato curioso sobre la Luna, en una oración.",
        "Dime un dato curioso sobre Júpiter, en una oración.",
        "Dime un dato curioso sobre Saturno, en una oración.",
    ]

    async def procesar(indice: int, pregunta: str):
        print(f"[{indice}] -> entrando a la cola (máx. 2 llamadas en paralelo)...")
        respuesta = await servicio.responder(pregunta)
        print(f"[{indice}] OK: {respuesta}")

    await asyncio.gather(*(procesar(i, p) for i, p in enumerate(preguntas, start=1)))


async def demo_circuit_breaker():
    print("\n" + "=" * 70)
    print("DEMO 2: Circuit Breaker - simulación de un agente que falla")
    print("=" * 70)

    tiempo_abierto = 3.0
    circuito = CircuitBreaker(umbral_fallos=2, tiempo_abierto_segundos=tiempo_abierto)

    async def agente_que_siempre_falla():
        raise RuntimeError("el modelo no está respondiendo (simulado)")

    for intento in range(1, 5):
        try:
            await circuito.ejecutar(agente_que_siempre_falla)
        except CircuitAbiertoError:
            print(f"[{intento}] circuito {circuito.estado.value}: rechazado sin intentar la llamada")
        except RuntimeError as error:
            print(f"[{intento}] circuito {circuito.estado.value}: falló la llamada ({error})")

    print(f"\nEsperando {tiempo_abierto:.0f}s a que el circuito pase a semi-abierto...")
    await asyncio.sleep(tiempo_abierto)

    async def agente_recuperado():
        return "ok"

    resultado = await circuito.ejecutar(agente_recuperado)
    print(f"circuito {circuito.estado.value}: la llamada de prueba tuvo éxito -> {resultado}")


if __name__ == "__main__":
    asyncio.run(demo_bulkhead())
    asyncio.run(demo_circuit_breaker())
