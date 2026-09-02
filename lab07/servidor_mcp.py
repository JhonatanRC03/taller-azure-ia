"""
Laboratorio 07 - Parte 2a: Servidor MCP personalizado
======================================================
Adaptación en español del laboratorio de Microsoft Learn "Connect an Azure AI
Agent to a remote MCP server" (sección "Create an MCP server with custom tools").

¿Qué es un servidor MCP?
-------------------------
MCP (Model Context Protocol) es un protocolo estándar para exponer "herramientas"
(funciones de Python) de forma que cualquier agente de IA compatible con MCP pueda
descubrirlas y llamarlas, sin importar en qué lenguaje esté escrito el servidor ni
el cliente. Aquí usamos la librería 'fastmcp' para crear ese servidor en pocas
líneas.

Este servidor simula el backend de una tienda de telescopios: expone dos
herramientas de solo lectura para consultar inventario y ventas semanales.
Un agente (ver 'cliente_mcp.py') podrá descubrir estas herramientas y usarlas
para responder preguntas o dar recomendaciones (por ejemplo: reabastecer o
liquidar productos).

Cómo se ejecuta:
- Este archivo NO se ejecuta manualmente. Es 'cliente_mcp.py' quien lo arranca
  automáticamente como subproceso, usando E/S estándar (stdio) como canal de
  comunicación (JSON-RPC sobre stdin/stdout).
"""

from fastmcp import FastMCP

# Crear el servidor MCP. El nombre es solo una etiqueta descriptiva.
mcp = FastMCP(name="InventarioTelescopios")


@mcp.tool()
def consultar_inventario() -> dict:
    """Devuelve las unidades disponibles en inventario para cada producto de la tienda."""
    return {
        "Telescopio Estándar": 6,
        "Telescopio Avanzado": 8,
        "Telescopio Premium": 28,
        "Cámara Astronómica": 5,
        "Filtro Solar": 12,
        "Ocular Gran Angular": 9,
        "Trípode Reforzado": 30,
        "Montura Ecuatorial": 3,
        "Filtro Lunar": 17,
        "Mochila de Transporte": 45,
    }


@mcp.tool()
def consultar_ventas_semanales() -> dict:
    """Devuelve las unidades vendidas/alquiladas la última semana para cada producto."""
    return {
        "Telescopio Estándar": 22,
        "Telescopio Avanzado": 18,
        "Telescopio Premium": 3,
        "Cámara Astronómica": 2,
        "Filtro Solar": 14,
        "Ocular Gran Angular": 19,
        "Trípode Reforzado": 4,
        "Montura Ecuatorial": 1,
        "Filtro Lunar": 13,
        "Mochila de Transporte": 17,
    }


# Esta tercera tool SÍ recibe parámetros (a diferencia de las dos de arriba, que
# no reciben nada). FastMCP arma el esquema JSON de "parameters" leyendo:
# - los tipos de cada argumento (precio_unitario: float, porcentaje_descuento: float)
# - la sección "Args:" del docstring, para la descripción de cada uno
# Así el cliente descubre, sin que nadie lo escriba a mano, qué parámetros pedir
# y qué significa cada uno.
@mcp.tool()
def calcular_precio_con_descuento(precio_unitario: float, porcentaje_descuento: float) -> dict:
    """Calcula el precio final de un producto luego de aplicarle un descuento.

    Args:
        precio_unitario: Precio original del producto, en dólares.
        porcentaje_descuento: Porcentaje de descuento a aplicar (de 0 a 100).
    """
    precio_final = round(precio_unitario * (1 - porcentaje_descuento / 100), 2)
    return {
        "precio_unitario": precio_unitario,
        "porcentaje_descuento": porcentaje_descuento,
        "precio_final": precio_final,
    }


if __name__ == "__main__":
    # show_banner=False evita imprimir el banner de inicio en stdout, ya que
    # eso rompería el protocolo MCP (que espera solo mensajes JSON-RPC por stdio).
    mcp.run(show_banner=False)
