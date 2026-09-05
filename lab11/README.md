# Lab11 - Orquestación multiagente secuencial con Agent Framework

Adaptación en español del laboratorio de Microsoft Learn **"Orchestrate a multi-agent
solution using Microsoft Agent Framework"** (carpeta
[`08-agent-orchestration`](https://github.com/MicrosoftLearning/mslearn-ai-agents/tree/main/Labfiles/08-agent-orchestration)
del repo `mslearn-ai-agents`).

Este laboratorio construye directamente sobre lab09/lab10: mismo `FoundryChatClient`,
mismo patrón de agentes de `agent-framework`. Lo nuevo aquí es **coordinar varios
agentes especializados** en una cadena, en vez de un solo agente que hace todo.

## Concepto clave: orquestación secuencial

En lab09 tenías un solo agente con una herramienta. Aquí tienes **tres agentes**, cada
uno con una única responsabilidad, encadenados en orden:

```
comentario del cliente
      │
      ▼
[resumidor]     → resume el comentario en una sola frase
      │
      ▼
[clasificador]  → clasifica ese resumen en una categoría
      │
      ▼
[accion]        → sugiere qué hacer, a partir del resumen + la categoría
      │
      ▼
respuesta final (con la salida de los 3 agentes)
```

Cada agente recibe como entrada la salida del anterior. Esto es útil para dividir una
tarea compleja en pasos simples y auditables (puedes ver exactamente qué dijo cada
agente), en vez de un solo prompt gigante que intenta hacer todo a la vez.

## Conceptos y API nuevos frente a lab09/lab10

| Concepto | Qué es |
|---|---|
| `chat_client.as_agent(name=, instructions=)` | Forma abreviada de crear un `Agent` a partir de un `FoundryChatClient` ya existente, sin repetir `client=` en cada uno. Útil cuando varios agentes comparten el mismo modelo. |
| `SequentialBuilder(participants=[...], output_from="all")` | Arma una **orquestación** (workflow multiagente): cada agente de `participants` procesa la salida del anterior, en el orden de la lista. `output_from="all"` hace que el resultado final incluya la respuesta de **cada** agente, no solo la del último. |
| `.build()` | Convierte el builder en un objeto `Workflow` ejecutable. |
| `await workflow.run(prompt)` | Ejecuta la cadena completa de principio a fin. |
| `resultado.get_outputs()` | Devuelve la lista de resultados de cada agente que participó, listos para inspeccionar. |
| `Message` (de `agent_framework`) | El tipo de cada mensaje individual dentro de una respuesta (`msg.author_name`, `msg.role`, `msg.text`). |

## Archivos de este laboratorio

| Archivo | Qué hace |
|---|---|
| [agentes.py](agentes.py) | Crea los 3 agentes especializados, arma la orquestación secuencial, la ejecuta con un comentario de cliente de ejemplo y muestra la salida de cada agente. |
| [.env](.env) | `AZURE_AI_PROJECT_ENDPOINT` y `AZURE_AI_MODEL_DEPLOYMENT_NAME` de tu proyecto/deployment en Foundry (mismos valores que usaste en lab09/lab10). |

## Requisitos previos

- Haber completado lab09 (mismo proyecto de Foundry y modelo desplegado sirven aquí).
- Haber iniciado sesión con `az login` (usa `AzureCliCredential`, igual que lab09/lab10).
- Paquetes instalados en el `.venv/` de la raíz (ya agregados a
  [requirements.txt](../requirements.txt)):
  - `agent-framework-foundry` (ya lo tenías de lab09/lab10)
  - `agent-framework-orchestrations` (nuevo: trae `SequentialBuilder` y otros patrones
    de orquestación — se instala limpio, sin el problema de dependencias del paquete
    completo `agent-framework`; ver notas de lab09).

## Configurar este laboratorio

1. Abre [.env](.env) en esta carpeta y reemplaza `your_project_endpoint` con el
   endpoint de tu proyecto de Foundry (el mismo de lab09/lab10).
2. Deja `AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-5` si usaste ese nombre de deployment.
3. Activa el entorno virtual de la raíz e inicia sesión en Azure:

   ```bash
   source ../.venv/bin/activate   # desde la carpeta lab11/
   az login
   ```

## Entender el código de `agentes.py`

1. **Imports**: `Message` (tipo de mensaje), `FoundryChatClient` (cliente de chat),
   `SequentialBuilder` (constructor de la orquestación), `AzureCliCredential`
   (autenticación con tu sesión de `az login`).
2. **Instrucciones de cada agente** (`instrucciones_resumidor`, `instrucciones_clasificador`,
   `instrucciones_accion`): son prompts de sistema cortos y específicos — cada agente
   solo sabe hacer UNA cosa.
3. **`FoundryChatClient(...)`**: igual que en lab09, se conecta al modelo desplegado
   usando `AZURE_AI_PROJECT_ENDPOINT` + `AZURE_AI_MODEL_DEPLOYMENT_NAME`.
4. **`chat_client.as_agent(...)`** (×3): crea los tres agentes especializados a partir
   del mismo cliente, cada uno con su propio nombre e instrucciones.
5. **`comentario`**: el texto de ejemplo que se procesará — un comentario de un cliente
   de la tienda de telescopios sobre la app de inventario.
6. **`SequentialBuilder(participants=[...], output_from="all").build()`**: arma el
   workflow con los tres agentes en el orden en que deben ejecutarse.
7. **`await workflow.run(...)`** + **`resultado.get_outputs()`**: ejecuta la cadena
   completa y recolecta la salida de cada paso.
8. **Bucle final**: recorre cada salida y cada mensaje dentro de ella, mostrando el
   nombre del agente (`msg.author_name`) y su texto (`msg.text`).

## Probar la aplicación

```bash
python agentes.py
```

Deberías ver algo como:

```
------------------------------------------------------------
01 [resumidor]
El cliente pide una opción de modo oscuro para usar la app cómodamente de noche.
------------------------------------------------------------
02 [clasificador]
Solicitud de función
------------------------------------------------------------
03 [accion]
Registrar como solicitud de mejora: agregar modo oscuro para mayor comodidad nocturna.
```

### Probar con otro comentario

Edita la variable `comentario` en `agentes.py` y prueba, por ejemplo:

```
Contacté al soporte de la tienda porque no podía acceder a mi cuenta. Me respondieron
casi de inmediato, fueron muy amables y resolvieron el problema en minutos. Sinceramente,
fue una de las mejores experiencias de soporte que he tenido.
```

Deberías ver una clasificación distinta (por ejemplo, "Elogio") y una acción coherente
con ese tipo de comentario.

Cuando termines, sal del entorno virtual con `deactivate`.

## Diferencias con lab09 (resumen)

| | lab09 (un solo agente) | lab11 (orquestación secuencial) |
|---|---|---|
| Cantidad de agentes | 1 (`AgenteReclamoGastos`) | 3 (`resumidor`, `clasificador`, `accion`) |
| Cómo se crean | `Agent(client=, name=, instructions=, tools=)` | `chat_client.as_agent(name=, instructions=)` (más corto, mismo cliente) |
| Herramientas (`@tool`) | Sí (`enviar_reclamo`) | No — aquí cada agente solo "piensa", no ejecuta funciones |
| Coordinación | No aplica (un solo agente) | `SequentialBuilder` encadena las salidas de un agente como entrada del siguiente |
| Ejecución | `await agente.run(mensajes)` | `await workflow.run(prompt)` + `resultado.get_outputs()` |
