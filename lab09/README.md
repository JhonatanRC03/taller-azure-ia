# Lab09 - Microsoft Agent Framework + Foundry Toolkit (agente de reclamos de gastos)

Adaptación en español del laboratorio de Microsoft Learn **"Create a Foundry project with
the Foundry Toolkit VS Code extension"** (carpeta
[`07-agent-framework`](https://github.com/MicrosoftLearning/mslearn-ai-agents/tree/main/Labfiles/07-agent-framework)
del repo `mslearn-ai-agents`).

A diferencia de los labs anteriores (que usaban `openai.OpenAI` con API key, o
`azure-ai-projects` con `AIProjectClient`), aquí conocerás el **Microsoft Agent
Framework** (`agent-framework` en PyPI): la nueva librería de Microsoft para
construir agentes en Python, y la extensión **Foundry Toolkit** para crear y
gestionar recursos de Azure AI Foundry sin salir de VS Code.

## Conceptos clave (antes de empezar)

| Concepto | Qué es |
|---|---|
| **Foundry Toolkit** (antes "AI Toolkit") | Extensión de VS Code para crear proyectos de Foundry, desplegar modelos del Model Catalog y gestionar agentes, sin usar el portal web. |
| **Proyecto de Foundry** | Contenedor de recursos (modelos desplegados, agentes, conexiones) dentro de un recurso de Azure AI Foundry. |
| **Model Catalog** | Catálogo de modelos disponibles para desplegar (OpenAI, Meta, Mistral, etc.). Aquí desplegarás `gpt-5`. |
| **Project Endpoint** | URL que identifica tu proyecto de Foundry. La usa el código para saber a qué proyecto conectarse. |
| **Microsoft Agent Framework** (`agent-framework`) | Librería Python (sucesora conceptual de Semantic Kernel/AutoGen) para definir agentes: modelo + instrucciones + herramientas, con una API async simple (`Agent`, `agent.run(...)`). |
| **`FoundryChatClient`** | El "cliente de chat" del Agent Framework que sabe hablar con un modelo desplegado en un proyecto de Foundry. Necesita `project_endpoint`, `model` (nombre del deployment) y `credential`. |
| **`AzureCliCredential`** | Reutiliza tu sesión de `az login` para autenticar las llamadas (no se usa una API key). |
| **`@tool`** | Decorador que convierte una función Python normal en una **herramienta** (function calling) que el modelo puede decidir invocar. `approval_mode="never_require"` hace que se ejecute automáticamente, sin pedir confirmación en cada llamada (a diferencia del flujo manual de aprobación MCP de lab07/lab08). |
| **`Agent`** | Agrupa el cliente, el nombre, las **instrucciones** (system prompt) y la lista de `tools`. Se usa con `async with` porque abre/cierra recursos internamente. |
| **`agent.run(mensajes)`** | Envía los mensajes al agente y devuelve la respuesta final, después de que el modelo decida (o no) usar las herramientas disponibles. |

## Archivos de este laboratorio

| Archivo | Qué hace |
|---|---|
| [agente_gastos.py](agente_gastos.py) | Carga los datos de gastos, define la herramienta `enviar_reclamo` (simula el envío de un correo) y crea un `Agent` que usa esa herramienta para redactar y "enviar" el reclamo. |
| [.env](.env) | `PROJECT_ENDPOINT` y `MODEL_DEPLOYMENT_NAME` de tu proyecto/deployment en Foundry. |
| [data/gastos.txt](data/gastos.txt) | Datos de ejemplo: gastos de un viaje a una conferencia (tema coherente con la tienda de telescopios de lab06/lab07). |

## Requisitos previos

- Extensión **Foundry Toolkit** instalada en VS Code (busca "Foundry Toolkit" en el
  Marketplace; en textos/comandos antiguos puede aparecer como "AI Toolkit" — es la
  misma extensión).
- Haber iniciado sesión con `az login` (el script usa `AzureCliCredential`, NO usa
  API keys como lab06/S1/chat).
- El paquete `agent-framework` instalado en el `.venv/` de la raíz del repo (ya
  agregado a [requirements.txt](../requirements.txt); si hace falta, instálalo con
  `pip install agent-framework`).

## Parte 1 - Crear el proyecto de Foundry con la extensión (portal desde VS Code)

1. Abre VS Code y ve a **Extensions** (`Ctrl+Shift+X`).
2. Busca **Foundry Toolkit** (de Microsoft) e instálala.
3. Abre su ícono en la barra lateral. Inicia sesión con tu cuenta de Azure si te lo pide.
4. En **Microsoft Foundry Resources**, selecciona **Create Project**.
   - Si ya tienes un proyecto activo, puedes crear uno nuevo haciendo clic derecho
     sobre el proyecto activo en **My Resources** > **Switch Default Project**.
5. Elige el **resource group** que quieras usar (por ejemplo, uno existente de tus
   labs anteriores) y ponle un nombre a tu proyecto, por ejemplo `proj-lab09-agentframework`.
6. Espera a que termine el despliegue. El proyecto aparecerá en el panel de Foundry
   Toolkit como el proyecto por defecto.

> **¿Por qué esto y no el portal web?** Es el mismo recurso de Foundry que
> creaste en lab08 desde https://ai.azure.com, pero la extensión te permite
> hacerlo (y desplegar modelos, y copiar el endpoint) sin cambiar de ventana.

## Parte 2 - Desplegar un modelo

1. Cuando aparezca el popup **"Project deployed successfully"**, haz clic en
   **Deploy a model** (o usa el ícono **+** junto a **Models**, o `F1` >
   **Foundry Toolkit: Show model catalog**).
2. En el Model Catalog, busca **gpt-5** y selecciona **Deploy**.
3. Configura el despliegue:
   - **Deployment name**: `gpt-5`
   - **Deployment type**: `Global Standard` (o `Standard` si no está disponible)
   - **Model version** y **Tokens per minute**: deja los valores por defecto
4. Selecciona **Deploy to Microsoft Foundry** y espera a que termine.
5. El modelo aparecerá bajo **Models** en la vista de Resources.
6. Haz clic derecho sobre el deployment y elige **Copy Project Endpoint**.
   - Si no encuentras esa opción, el endpoint también está en el portal
     (https://ai.azure.com) en el campo **Microsoft Foundry project endpoint**
     de la página Home del proyecto.

## Parte 3 - Configurar este laboratorio

1. Abre [.env](.env) en esta carpeta y reemplaza `your_project_endpoint` con el
   endpoint que copiaste. Deja `MODEL_DEPLOYMENT_NAME=gpt-5` si usaste ese nombre.
2. Activa el entorno virtual de la raíz del repo e inicia sesión en Azure:

   ```bash
   source ../.venv/bin/activate   # desde la carpeta lab09/
   az login
   ```

3. Confirma que `agent-framework` esté instalado:

   ```bash
   pip show agent-framework
   ```

   Si no aparece, instálalo con `pip install -r ../requirements.txt` (ya lo
   agregamos ahí) o `pip install agent-framework`.

## Parte 4 - Entender el código de `agente_gastos.py`

El archivo ya está completo (no necesitas escribir nada), pero aquí va la
explicación de cada bloque, siguiendo el mismo orden que el lab original:

1. **Imports** (`from agent_framework import tool, Agent`,
   `from agent_framework.foundry import FoundryChatClient`,
   `from azure.identity import AzureCliCredential`, `pydantic.Field`,
   `typing.Annotated`): traen las clases del Agent Framework, la credencial de
   Azure CLI, y las utilidades de `pydantic`/`typing` para describir los
   parámetros de la herramienta con metadatos que el modelo puede leer.
2. **`main()`**: limpia la consola, carga `data/gastos.txt`, le pregunta al
   usuario qué quiere hacer con esos datos, y llama a `procesar_gastos(...)`.
3. **`enviar_reclamo(...)`** (la herramienta): decorada con `@tool(approval_mode="never_require")`.
   Cada parámetro usa `Annotated[tipo, Field(description="...")]` para que el
   modelo entienda qué debe pasarle a cada argumento (a quién, asunto, cuerpo).
   Solo imprime el correo en consola — **simula** el envío, no manda un correo real.
4. **`FoundryChatClient(...)`**: se conecta al modelo desplegado usando
   `PROJECT_ENDPOINT` + `MODEL_DEPLOYMENT_NAME` del `.env`, autenticado con
   `AzureCliCredential()` (tu sesión de `az login`).
5. **`Agent(...)`** (con `async with`): define el agente `AgenteReclamoGastos`
   con instrucciones que le dicen exactamente qué hacer (crear el reclamo,
   llamar a `enviar_reclamo` con el correo indicado, confirmar al usuario) y
   le da acceso a la herramienta con `tools=[enviar_reclamo]`.
6. **`agente.run(mensajes_prompt)`**: envía el prompt del usuario junto con los
   datos de gastos. El modelo decide llamar a `enviar_reclamo` con los datos
   procesados, y luego devuelve una respuesta de confirmación que se imprime.

## Parte 5 - Probar la aplicación

1. Desde la carpeta `lab09/` (con el venv activado y sesión de `az login` ya
   iniciada), ejecuta:

   ```bash
   python agente_gastos.py
   ```

2. Cuando te pregunte qué quieres hacer con los datos de gastos, escribe:

   ```
   Envía un reclamo de gastos
   ```

3. Revisa la salida: el agente debería componer un correo con el reclamo de
   gastos (impreso en consola por la herramienta `enviar_reclamo`) y luego
   confirmarte que lo hizo.

> **Tip**: si falla por límite de tasa (*rate limit*), espera unos segundos y
> vuelve a intentar. Si tu suscripción no tiene cuota suficiente, el modelo
> podría no responder — revisa la cuota del deployment en el portal de Foundry.

4. Cuando termines, sal del entorno virtual con `deactivate`.

## Diferencias con los labs anteriores (resumen)

| | lab06/lab07/S1/chat | lab08 | lab09 |
|---|---|---|---|
| Cliente | `openai.OpenAI(base_url=..., api_key=...)` | `azure-ai-projects` (`AIProjectClient`) | `agent-framework` (`FoundryChatClient`) |
| Autenticación | API key | `DefaultAzureCredential` (`az login`) | `AzureCliCredential` (`az login`) |
| Definición del agente | No hay "agente" como objeto; se arma el prompt/tools a mano en cada llamada | Se crea y configura en el **portal** (fuera del código) | Se define **en código Python** con la clase `Agent` |
| Herramientas | Function calling manual con `client.responses.create(tools=[...])` (lab06) o servidor MCP (lab07) | Base de conocimiento Foundry IQ conectada en el portal | `@tool` de `agent-framework` sobre una función Python normal |
| Aprobación de herramientas | No aplica / MCP manual (lab07) | Aprobación manual de llamadas MCP (lab08) | `approval_mode="never_require"` (automática) |
