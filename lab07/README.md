# Lab07 - Integración con MCP (Model Context Protocol)

Adaptación en español del laboratorio de Microsoft Learn **"Connect an Azure AI Agent to a
remote MCP server"** (carpeta `03-mcp-integration` del repo
[mslearn-ai-agents](https://github.com/MicrosoftLearning/mslearn-ai-agents)).

Igual que en `lab06/`, aquí usamos el cliente estándar de `openai` (clase `OpenAI`)
apuntando al recurso de Azure OpenAI configurado en el `.env` de la raíz del proyecto
(`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`), en lugar de
`azure-ai-projects` + `az login` (que requeriría además un proyecto de Azure AI Foundry con
`PROJECT_ENDPOINT`). El concepto de MCP es exactamente el mismo; solo cambia el cliente que
lo usa.

## ¿Qué es MCP?

**MCP (Model Context Protocol)** es un protocolo estándar y abierto para exponer
"herramientas" (funciones) que un agente de IA puede descubrir y llamar, sin importar en
qué lenguaje esté escrito el servidor que las expone ni el cliente que las consume. En este
laboratorio vas a ver **dos formas** de usar MCP con un agente:

1. **Conectarte a un servidor MCP remoto que ya existe** (el de documentación de Microsoft
   Learn), sin escribir ni una línea de las herramientas que ofrece.
2. **Crear tu propio servidor MCP** con herramientas personalizadas y conectarlo a un
   agente mediante un cliente MCP.

## Archivos de este laboratorio

| Archivo | Qué hace | Parte del lab original |
|---|---|---|
| [agente_documentacion.py](agente_documentacion.py) | Agente que usa una tool de tipo `mcp` para consultar el servidor remoto de documentación de Microsoft Learn (`https://learn.microsoft.com/api/mcp`). | `agent.py` |
| [servidor_mcp.py](servidor_mcp.py) | Servidor MCP propio (con `FastMCP`) que expone 2 herramientas: consultar inventario y ventas semanales de una tienda de telescopios. | `server.py` |
| [cliente_mcp.py](cliente_mcp.py) | Cliente MCP que arranca `servidor_mcp.py`, descubre sus herramientas y las conecta a un agente conversacional de inventario. | `client.py` |

## Orden recomendado para entenderlo (qué ver primero)

1. **Lee primero [servidor_mcp.py](servidor_mcp.py)**. Es el archivo más simple: solo
   define dos funciones normales de Python decoradas con `@mcp.tool()`. Entender esto te da
   la base de "qué es una herramienta MCP" antes de ver cómo se conecta a un agente.
2. **Corre y lee [agente_documentacion.py](agente_documentacion.py)**. Es el ejemplo más
   corto para entender el flujo de **aprobación de llamadas MCP** (`mcp_approval_request` /
   `mcp_approval_response`), usando un servidor remoto que no tienes que programar tú.
3. **Corre y lee [cliente_mcp.py](cliente_mcp.py)** al final. Es el más completo: combina
   arrancar tu propio servidor MCP como subproceso, descubrir sus herramientas
   dinámicamente y traducirlas al formato de "function tool" que entiende el modelo.

## Cómo funciona cada parte (resumen conceptual)

### 1. Agente + servidor MCP remoto (`agente_documentacion.py`)

1. Se define una *tool* de tipo `"mcp"` con la URL del servidor remoto y
   `require_approval: "always"` (para que cada llamada deba autorizarse antes de
   ejecutarse; útil para auditar qué hace el agente).
2. Se envía la pregunta del usuario junto con esa tool.
3. Si el modelo decide usar el servidor MCP, la respuesta no ejecuta nada todavía: trae uno
   o más bloques `mcp_approval_request` pidiendo autorización.
4. El script responde automáticamente con `mcp_approval_response` (`approve=True`) por cada
   solicitud pendiente, y vuelve a llamar al modelo pasando todo el historial acumulado
   (sin usar `previous_response_id`, para mantener el mismo estilo "sin estado" que el resto
   del repo).
5. Se repite el paso 3-4 hasta que ya no haya más solicitudes de aprobación pendientes.
   Ahí `response.output_text` trae la respuesta final en lenguaje natural.

### 2. Servidor MCP personalizado (`servidor_mcp.py`)

- Usa la librería `fastmcp` para crear un servidor MCP en pocas líneas.
- Cada función decorada con `@mcp.tool()` queda registrada y es descubrible por cualquier
  cliente MCP que se conecte.
- Este archivo **no se ejecuta manualmente**: `cliente_mcp.py` lo arranca automáticamente
  como subproceso y se comunica con él por `stdio` (entrada/salida estándar), usando
  mensajes JSON-RPC.

### 3. Cliente MCP + agente de inventario (`cliente_mcp.py`)

1. Arranca `servidor_mcp.py` como subproceso (`StdioServerParameters` + `stdio_client`) y
   abre una sesión MCP (`ClientSession`).
2. Le pregunta al servidor qué herramientas tiene (`session.list_tools()`).
3. Convierte cada herramienta MCP descubierta en una "function tool" (el formato que espera
   la Responses API) usando el esquema JSON que ya trae cada herramienta.
4. En cada turno de la conversación, si el modelo pide ejecutar una función, el script la
   reenvía al servidor real vía `session.call_tool(nombre, argumentos)`, obtiene el
   resultado y se lo devuelve al modelo como `function_call_output`.
5. Con instrucciones de sistema tipo "recomienda reabastecer si el inventario < 10 y las
   ventas semanales > 15", el agente puede razonar con datos reales que vienen del servidor
   MCP, no de datos que estén "hardcodeados" en el prompt.

## Requisitos previos

Desde la raíz del proyecto (con el entorno virtual `.venv` activado):

```bash
pip install -r requirements.txt
```

Esto instala, entre otras cosas, `mcp` y `fastmcp` (necesarias para las partes 2 y 3 de este
laboratorio). El primer arranque de `servidor_mcp.py` puede tardar varios segundos, ya que
`fastmcp` carga bastantes dependencias la primera vez.

## Cómo ejecutarlo

Desde la carpeta `lab07`:

```bash
# Parte 1: agente + servidor MCP remoto de documentación
python agente_documentacion.py
```

```bash
# Parte 2 y 3: cliente MCP + servidor MCP propio (inventario de telescopios)
python cliente_mcp.py
```

Prueba con preguntas como:

```
Muéstrame el inventario actual de todos los productos.
```

```
¿Qué productos deberían reabastecerse?
```

```
¿Qué productos recomendarías liquidar?
```

```
Si un telescopio premium cuesta 500 dolares y le aplico 15% de descuento, cuanto queda?
```

Escribe `salir` para terminar la conversación en `cliente_mcp.py`.

> **Nota**: `servidor_mcp.py` no se ejecuta por separado; siempre es lanzado
> automáticamente por `cliente_mcp.py`.

## Diferencias con el laboratorio original de Microsoft Learn

- El original usa `azure-ai-projects` (`AIProjectClient`, `PromptAgentDefinition`) y
  `az login` para crear "agentes" versionados dentro de un proyecto de Azure AI Foundry.
  Aquí, igual que en `lab06/`, se usa directamente el cliente `openai.OpenAI` apuntando al
  endpoint de Azure OpenAI configurado en `.env`, sin necesidad de `az login` ni de un
  `PROJECT_ENDPOINT`.
- El original mantiene el estado de la conversación con `openai_client.conversations.create()`
  y `previous_response_id`. Aquí se mantiene manualmente una lista de mensajes (`mensajes`)
  que se reenvía completa en cada llamada, igual que en `lab06/agente.py`.
