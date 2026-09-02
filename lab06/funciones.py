"""
Laboratorio 06 - Funciones personalizadas para el agente
=========================================================
Este archivo contiene las funciones "reales" de Python que el agente de IA
podrá invocar como herramientas (function tools). El modelo NUNCA ejecuta
este código directamente: solo decide CUÁNDO llamarlas y con QUÉ argumentos.
Es nuestro programa (agente.py) el que realmente ejecuta la función en Python
y le devuelve el resultado al modelo.

Igual que en el laboratorio original de Microsoft Learn, los datos NO están
escritos directamente en el código: se leen desde archivos de texto ubicados
en la carpeta 'data/'. Así, funciones.py solo contiene lógica, y los datos
(eventos, tarifas, prioridades) se pueden editar sin tocar el código Python.

Cada función retorna un string en formato JSON, porque así es como se debe
enviar el resultado de vuelta al modelo (como "function_call_output").
"""

import json
from datetime import datetime

# --------------------------------------------------------------------------
# Carga de datos desde archivos de texto (carpeta data/)
# --------------------------------------------------------------------------

def _cargar_eventos(ruta: str = "data/eventos.txt") -> list:
    """Lee data/eventos.txt y devuelve una lista de eventos ordenada por fecha.

    Cada línea del archivo tiene el formato:
        nombre|tipo|MM-DD|continente1;continente2;...
    """
    eventos = []
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            partes = linea.strip().split("|")
            if len(partes) == 4:
                mes, dia = map(int, partes[2].split("-"))
                eventos.append((
                    partes[0],                      # nombre
                    partes[1],                      # tipo
                    mes * 100 + dia,                # fecha como entero MMDD para poder comparar/ordenar
                    partes[2],                      # fecha en texto "MM-DD"
                    set(partes[3].split(";")),      # continentes donde es visible
                ))
    eventos.sort(key=lambda evento: evento[2])
    return eventos


def _cargar_tarifas(ruta: str) -> dict:
    """Lee un archivo 'clave|valor' (una por línea) y lo devuelve como diccionario.

    Se usa tanto para las tarifas de telescopio como para los multiplicadores
    de prioridad, ya que ambos archivos comparten el mismo formato simple.
    """
    tarifas = {}
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            partes = linea.strip().split("|")
            if len(partes) == 2:
                tarifas[partes[0]] = float(partes[1])
    return tarifas


# Datos cargados una sola vez al importar el módulo
EVENTOS = _cargar_eventos()
TARIFAS_BASE = _cargar_tarifas("data/tarifas_telescopio.txt")
MULTIPLICADOR_PRIORIDAD = _cargar_tarifas("data/multiplicadores_prioridad.txt")


# Determina el próximo evento astronómico visible para una ubicación dada
def proximo_evento_visible(ubicacion: str) -> str:
    """Devuelve el próximo evento astronómico visible desde una ubicación (continente)."""
    hoy = int(datetime.now().strftime("%m%d"))
    ubic = ubicacion.lower().replace(" ", "_")

    # Recorremos los eventos (ya ordenados por fecha) y devolvemos el primero
    # que sea visible desde la ubicación indicada y que todavía no haya pasado.
    for nombre, tipo, fecha, fecha_str, continentes in EVENTOS:
        if ubic in continentes and fecha >= hoy:
            return json.dumps({
                "evento": nombre,
                "tipo": tipo,
                "fecha": fecha_str,
                "visible_desde": sorted(continentes),
            }, ensure_ascii=False)

    return json.dumps(
        {"mensaje": f"No se encontraron próximos eventos para '{ubicacion}'."},
        ensure_ascii=False,
    )


# Calcula el costo de una observación según el telescopio, las horas y la prioridad
def calcular_costo_observacion(nivel_telescopio: str, horas: float, prioridad: str) -> str:
    """Calcula el costo (en USD) de alquilar un telescopio para una observación."""
    nivel = nivel_telescopio.lower()
    prio = prioridad.lower()

    if nivel not in TARIFAS_BASE:
        return json.dumps({
            "error": f"Nivel de telescopio desconocido: '{nivel_telescopio}'. "
                     f"Opciones válidas: {', '.join(TARIFAS_BASE)}"
        }, ensure_ascii=False)
    if prio not in MULTIPLICADOR_PRIORIDAD:
        return json.dumps({
            "error": f"Prioridad desconocida: '{prioridad}'. "
                     f"Opciones válidas: {', '.join(MULTIPLICADOR_PRIORIDAD)}"
        }, ensure_ascii=False)
    if horas <= 0:
        return json.dumps({"error": "Las horas deben ser mayores que cero."}, ensure_ascii=False)

    tarifa_hora = TARIFAS_BASE[nivel]
    multiplicador = MULTIPLICADOR_PRIORIDAD[prio]
    costo_base = tarifa_hora * horas
    costo_total = costo_base * multiplicador

    return json.dumps({
        "nivel_telescopio": nivel,
        "horas": horas,
        "tarifa_hora": tarifa_hora,
        "prioridad": prio,
        "multiplicador_prioridad": multiplicador,
        "costo_base": costo_base,
        "costo_total": costo_total,
    }, ensure_ascii=False)


# Genera un reporte de texto que resume una observación astronómica
def generar_reporte_observacion(
    nombre_evento: str,
    ubicacion: str,
    nivel_telescopio: str,
    horas: float,
    prioridad: str,
    nombre_observador: str,
) -> str:
    """Genera y guarda en disco un reporte de texto con el resumen de la observación."""
    # Reutilizamos las otras dos funciones para no duplicar lógica de cálculo/búsqueda
    costo = json.loads(calcular_costo_observacion(nivel_telescopio, horas, prioridad))
    evento = json.loads(proximo_evento_visible(ubicacion))

    if "error" in costo:
        return json.dumps(costo, ensure_ascii=False)

    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M")
    slug = nombre_evento.lower().replace(" ", "_")
    nombre_archivo = f"reporte_{slug}_{marca_tiempo.replace(':', '').replace(' ', '_')}.txt"

    reporte = f"""======================================
  OBSERVATORIOS CONTOSO - REPORTE DE SESIÓN
======================================
Fecha:          {marca_tiempo}
Observador:     {nombre_observador}
Evento:         {nombre_evento}
Ubicación:      {ubicacion}

PRÓXIMO EVENTO VISIBLE
  Evento:       {evento.get('evento', 'N/D')}
  Fecha:        {evento.get('fecha', 'N/D')}

RESERVA DE TELESCOPIO
  Nivel:            {costo['nivel_telescopio']}
  Horas:            {costo['horas']}
  Tarifa por hora:  ${costo['tarifa_hora']:.2f}
  Prioridad:        {costo['prioridad']}
  Multiplicador:    {costo['multiplicador_prioridad']}x

RESUMEN DE COSTOS
  Costo base:   ${costo['costo_base']:.2f}
  Costo total:  ${costo['costo_total']:.2f}
======================================
"""

    with open(nombre_archivo, "w", encoding="utf-8") as archivo:
        archivo.write(reporte)

    return json.dumps({
        "estado": "Reporte generado",
        "archivo": nombre_archivo,
    }, ensure_ascii=False)
