# Lab08 - Foundry IQ (base de conocimiento gestionada) + agente MCP con aprobación

Adaptación en español del laboratorio de Microsoft Learn **"Integrate an agent with
Foundry IQ"** (carpeta [`04-integrate-agent-with-foundry-iq`](https://github.com/MicrosoftLearning/mslearn-ai-agents/tree/main/Labfiles/04-integrate-agent-with-foundry-iq)
del repo `mslearn-ai-agents`).

A diferencia de lab06 y lab07 (donde todo el código y las herramientas viven en
Python), **la mayor parte de este laboratorio se hace en el portal de Azure AI
Foundry** (https://ai.azure.com). El único archivo Python es un cliente que se
conecta al agente ya configurado en el portal.

## ¿Qué es Foundry IQ?

Un modelo de lenguaje tiene una fecha de corte de conocimiento y no sabe nada de
tus datos privados (por ejemplo, tu catálogo de productos). **Foundry IQ** es la
función de Azure AI Foundry / Azure AI Search que resuelve esto creando una
**base de conocimiento** (*knowledge base*) configurable:

- Se conecta a una o varias **fuentes de conocimiento** (*knowledge sources*):
  Azure Blob Storage, SharePoint, OneLake, datos web, etc.
- Cuando el agente necesita responder algo, invoca la base de conocimiento y
  ocurre la **recuperación agéntica** (*agentic retrieval*):
  1. Descompone la pregunta del usuario en subconsultas.
  2. Ejecuta esas subconsultas en paralelo (búsqueda por palabra clave, vectorial
     o híbrida).
  3. Reordena los resultados por relevancia semántica (*semantic reranking*).
  4. Sintetiza una respuesta unificada con referencias a las fuentes (citas).
- Una misma base de conocimiento puede conectarse a **varios agentes**.
- La conexión entre el agente y la base de conocimiento usa **MCP** por debajo:
  Azure AI Search expone la herramienta `knowledge_base_retrieve` como un
  servidor MCP, igual que en lab07 pero ahora gestionado por el portal en vez
  de por ti.

En resumen: Foundry IQ = "RAG (Retrieval-Augmented Generation) gestionado", con
indexado automático, reranking y citas, sin que tengas que escribir el pipeline
de búsqueda a mano.

> Fuentes: [What is Foundry IQ?](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq) ·
> [Foundry IQ FAQ](https://learn.microsoft.com/azure/foundry/agents/concepts/foundry-iq-faq) ·
> [Connect a Foundry IQ knowledge base to Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/foundry-iq-connect)

## Archivos de este laboratorio

| Archivo | Qué hace |
|---|---|
| [agente_cliente.py](agente_cliente.py) | Cliente Python que se conecta al agente `product-expert-agent` creado en el portal, mantiene una conversación con estado (`conversations` API) y resuelve el ciclo de aprobación MCP cuando el agente usa Foundry IQ. |
| [.env](.env) | `PROJECT_ENDPOINT` y `AGENT_NAME` de tu proyecto/agente en Foundry. |

## Requisitos previos

- Una suscripción de Azure donde puedas crear recursos (Foundry, Azure AI
  Search, Storage Account).
- Haber iniciado sesión con `az login` (el script usa `DefaultAzureCredential`,
  NO usa API keys como el resto del repo).
- El entorno virtual del repo (`.venv/`) ya tiene instalados `azure-ai-projects`,
  `azure-identity`, `openai` y `python-dotenv` (ver [requirements.txt](../requirements.txt)
  de la raíz), así que no hace falta crear un venv nuevo para este lab.

## Parte 1 - Portal de Azure AI Foundry

### 1.1 Crear el proyecto

1. Entra a https://ai.azure.com y confirma que el toggle **New Foundry** esté
   activado.
2. En el selector de proyectos, elige **Create a new project** y dale un
   nombre (por ejemplo `lab08-foundry-iq`).
3. Confirma/crea el recurso de Foundry, la suscripción, el grupo de recursos y
   una región donde tengas cuota disponible.
4. Espera a que termine el aprovisionamiento.

### 1.2 Crear el agente

1. En la página del proyecto, ve a **Build** > **Agents** > **Create agent**.
2. Nómbralo `product-expert-agent`. Se creará con un modelo por defecto
   (por ejemplo `gpt-5`) ya desplegado.

### 1.3 Configurar instrucciones y conectar Foundry IQ

1. En el editor del agente, pega estas instrucciones:

   ```
   You are a helpful AI assistant for Contoso, specializing in outdoor camping and hiking products.
   You must ALWAYS search the knowledge base to answer questions about our products or product
   catalog. Provide detailed, accurate information and always cite your sources.
   If you don't find relevant information in the knowledge base, say so clearly.
   ```

2. **Save**.
3. En la sección **Knowledge**, despliega **Add** > **Connect to Foundry IQ**.
4. Elige **Connect to an AI Search resource** > **Create new resource** y crea
   un servicio de Azure AI Search (mismo grupo de recursos y región que el
   proyecto; pricing tier **Free** si está disponible).

### 1.4 Subir los documentos de productos

1. Descarga y descomprime
   [`contoso-products.zip`](https://github.com/MicrosoftLearning/mslearn-ai-agents/raw/main/Labfiles/04-integrate-agent-with-foundry-iq/data/contoso-products.zip)
   (3 PDFs: tiendas de campaña, mochilas, accesorios de camping).
2. En el [portal de Azure](https://portal.azure.com), crea un **Storage
   account** (mismo grupo de recursos/región que el proyecto, Standard, LRS).
3. En el storage account, **Upload** > crea un contenedor `contosoproducts` y
   sube los 3 PDFs.
4. En el servicio de Azure AI Search que creaste, ve a **Security + networking**
   > **Keys** y pon **API Access control** en **Both**.

### 1.5 Crear la base de conocimiento (knowledge base)

1. Vuelve a la pestaña de Foundry (refresca la página) y confirma que estás en
   **Knowledge** > **Create a knowledge base**, con **Azure Blob Storage**
   como fuente > **Connect**.
2. Configura:
   - **Name**: `ks-contosoproducts`
   - **Storage account** / **Container**: el storage y contenedor creados
   - **Authentication type**: API Key
   - **Content extraction mode**: minimal
   - **Embedding model**: el modelo desplegado (p. ej. `text-embedding-3-small`)
   - **Chat completions model**: el modelo desplegado (p. ej. `gpt-5`)
3. **Create**, elige el modelo de chat completions de nuevo si te lo pide, y
   **Save knowledge base**. Refresca hasta que el estado sea **active**.
4. Vuelve a **Knowledge** > **Manage** (junto al dropdown de conexión) >
   **Connected resources** > selecciona tu servicio de búsqueda > sección
   **Authentication** > **Key authentication** > **Edit authentication** y
   pega una de las claves del servicio de búsqueda (Azure Portal > tu
   servicio de búsqueda > **Keys**). **Save**.

### 1.6 Probar en el playground

1. Ve a **Build** > **Agents** > tu agente. En **Tools**:
   - **Elimina** la tool **Web Search** (se agrega sola y no es compatible con
     este flujo; si se queda, el agente falla antes de intentar usar la base
     de conocimiento).
   - No hace falta agregar nada más desde el diálogo **Seleccionar una
     herramienta** (ese catálogo son tools genéricas — Azure AI Search, Work
     IQ, Fabric IQ, SharePoint, etc. — y ahí **no** aparece nada con prefijo
     `kb-knowledgebase...`). Tu base de conocimiento Foundry IQ ya quedó
     conectada en la sección **Conocimiento** (verás algo como
     `knowledgebase354` listado ahí); eso es lo que necesitas.
   - El nombre con prefijo `kb-knowledgebase...` solo se ve más adelante,
     dentro de la extensión Foundry Toolkit para VS Code (paso 1.7).
2. Prueba preguntas como:
   - `What types of tents does Contoso offer?`
   - `Tell me about which backpacks are available in XL.`
   - `What camping accessories are available?`
3. Anota el **Agent name** (`product-expert-agent`) y el **Project endpoint**
   (página Home del proyecto) — los necesitas para el `.env`.

### 1.7 Exigir aprobación para las llamadas a la herramienta

El portal no tiene un control para esto todavía, así que se hace con la
extensión **Foundry Toolkit for VS Code**:

1. Instala la extensión **Foundry Toolkit** desde el marketplace de VS Code
   (a veces aparece como "AI Toolkit" en textos/comandos antiguos; es la
   misma extensión).
2. Abre su icono en la barra lateral, inicia sesión con tu cuenta de Azure.
3. En **Microsoft Foundry Resources** > **Set Default Project**, elige tu
   proyecto.
4. Bajo **Prompt Agents**, abre `product-expert-agent` (Agent Builder).
5. En **Tools**, ubica la tool `kb-knowledgebase...`, abre el menú **…** >
   **Ask for approval for all tools** y guarda.

Con esto, cada vez que el agente quiera consultar Foundry IQ, la llamada
quedará pendiente de aprobación — que es justo lo que maneja `agente_cliente.py`.

## Parte 2 - Cliente Python

1. Abre [.env](.env) y reemplaza `PROJECT_ENDPOINT` con el endpoint copiado en
   el paso 1.6 (tiene la forma
   `https://<recurso>.services.ai.azure.com/api/projects/<proyecto>`).
   Deja `AGENT_NAME=product-expert-agent` si usaste ese nombre.
2. Activa el entorno virtual de la raíz del repo e inicia sesión en Azure:

   ```bash
   source ../.venv/bin/activate   # desde la carpeta lab08/
   az login
   ```

3. Ejecuta el cliente:

   ```bash
   python agente_cliente.py
   ```

4. Prueba estas preguntas (aprobando cada solicitud MCP con `si`):

   ```
   What types of outdoor products does Contoso offer?
   Tell me about the weatherproof features of your tents.
   What's the difference between your daypacks and expedition backpacks?
   What camping accessories would you recommend for a weekend hiking trip?
   How much do those items typically cost?
   ```

   La última pregunta no debería necesitar aprobación nueva si el agente
   puede responder con el contexto de la conversación — así compruebas que el
   historial (`conversations` API del lado del servidor) se mantiene.
5. Escribe `history` para ver el historial acumulado y `quit` para salir.

## Cómo funciona `agente_cliente.py` (resumen conceptual)

1. `conectar_agente()`: crea un `AIProjectClient` con `DefaultAzureCredential`
   (usa la sesión de `az login`), obtiene un cliente `openai` "enchufado" al
   proyecto (`get_openai_client()`), busca el agente por nombre
   (`project_client.agents.get(agent_name=...)`) y abre una conversación
   (`openai_client.conversations.create(items=[])`) cuyo estado vive en el
   servidor.
2. `enviar_mensaje(...)`: agrega el mensaje del usuario a la conversación y
   pide una respuesta con `responses.create(conversation=..., agent_reference=...)`.
   El modelo y las herramientas (incluida Foundry IQ) ya están fijados en la
   configuración del agente hecha en el portal — el script no los declara.
3. Si el agente quiere usar Foundry IQ, la respuesta trae uno o más
   `mcp_approval_request`. `pedir_aprobaciones(...)` se los muestra al usuario
   en la terminal y arma las respuestas (`mcp_approval_response`). El bucle se
   repite hasta que ya no queden solicitudes pendientes.
4. `mostrar_historial(...)` imprime el historial que el script va guardando
   localmente (además del que ya vive en el servidor vía `conversation.id`).

## Diferencias frente a lab07

| | lab07 | lab08 |
|---|---|---|
| Dónde se define el agente | En código Python | En el portal de Azure AI Foundry |
| Cliente usado | `openai.OpenAI` + endpoint de Azure OpenAI | `azure-ai-projects` (`AIProjectClient`) + `openai` obtenido de `get_openai_client()` |
| Autenticación | API key (`.env` de la raíz) | `DefaultAzureCredential` (`az login`) |
| Estado de la conversación | Lista de mensajes reenviada en cada turno | `conversations` API (estado en el servidor, se referencia por `id`) |
| Herramienta MCP | Servidor remoto de Microsoft Learn Docs o servidor propio con FastMCP | Base de conocimiento Foundry IQ (Azure AI Search), expuesta como tool `kb-knowledgebase...` |
| Aprobación de llamadas | `require_approval: "always"` en el código | Se configura en el agente desde el Foundry Toolkit (VS Code) |
