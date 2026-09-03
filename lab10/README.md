# Lab10 - Dos formas de desplegar un agente hecho con Agent Framework

Este laboratorio no agrega conceptos nuevos de agentes (para eso ya está lab09):
se enfoca 100% en **cómo se despliega** un agente ya construido con
`agent-framework`, comparando dos formas:

| | [`autoalojado/`](autoalojado/) | [`hosted/`](hosted/) |
|---|---|---|
| ¿Qué es? | Tu script corre como un proceso normal, en cualquier hosting que elijas | Foundry registra tu código como una **entidad de agente** propia, versionada |
| ¿Aparece en el portal de Foundry (Build > Agents)? | No | Sí |
| ¿Cómo se expone? | Se ejecuta y termina (o corre en un loop propio) | Servidor HTTP que habla el protocolo "Responses" de Foundry |
| Versionado / rollback | Manual (tú lo gestionas) | Automático, cada `azd deploy` crea una versión nueva |
| Observabilidad / evaluación | Nada integrado | Logs, trazas y evaluación integrados en el portal |
| Autenticación recomendada en producción | La que tú configures (ideal: Managed Identity) | Managed Identity gestionada por la infraestructura de azd |
| ¿Se usa a diario en producción? | Poco (casos muy simples o de nicho) | **Sí — es el camino recomendado por Microsoft para producción** |

> 🎯 Si vas a memorizar una sola cosa de este lab: **en producción, usa Hosted
> Agent** (carpeta `hosted/`). La versión autoalojada existe aquí solo para que
> veas la diferencia de forma clara.

## Parte 1 - Autoalojado (`autoalojado/`)

### El concepto

Es el mismo patrón de código que ya usaste en `lab09/agente_gastos.py`: un
script de Python que crea un `Agent`, lo ejecuta una vez con `asyncio.run(...)`,
imprime la respuesta y termina. "Desplegarlo" significa únicamente correr ese
proceso en algún lugar que no sea tu laptop.

### Archivos

- [agente_autoalojado.py](autoalojado/agente_autoalojado.py) — el agente (idéntico en espíritu a lab09, con una herramienta de inventario más simple).
- [Dockerfile](autoalojado/Dockerfile) — cómo empaquetarlo en una imagen de contenedor.
- [.env](autoalojado/.env) / [requirements.txt](autoalojado/requirements.txt)

### Cómo se "despliega" (paso a paso conceptual)

1. Escribes el código del agente (ya está hecho aquí).
2. Lo empaquetas — por ejemplo con el `Dockerfile` de esta carpeta:
   ```bash
   cd lab10/autoalojado
   docker build -t agente-inventario-autoalojado .
   ```
3. Subes la imagen a un registro de contenedores (Azure Container Registry,
   Docker Hub, etc.).
4. Eliges DÓNDE correrla: Azure Container Apps, App Service for Containers,
   una VM, un Azure Function con contenedor personalizado... Cualquiera sirve,
   porque para Azure esto es "un contenedor más" — no sabe que es un "agente".
5. Configuras las variables de entorno (`PROJECT_ENDPOINT`, `MODEL_DEPLOYMENT_NAME`)
   y, en producción, cambiarías `AzureCliCredential` por una **Managed Identity**
   (no puedes hacer `az login` dentro de un contenedor en producción).
6. Listo — corre, pero **Foundry no sabe que existe como "agente"**: solo ve
   llamadas al modelo, como cualquier llamada de API.

### Por qué NO es el camino recomendado para producción

- No tienes versionado del agente en sí (solo el de tus propias imágenes/tags).
- No tienes trazas, evaluación ni métricas de calidad integradas en el portal
  de Foundry — tendrías que montar tu propia observabilidad desde cero.
- Cada vez que quieres invocarlo, necesitas tu propia capa de API/mensajería
  (Foundry no te da un endpoint de invocación administrado para esto).
- Manejar secretos, escalado, reinicios ante fallos, etc. es 100% tu
  responsabilidad.

## Parte 2 - Hosted Agent (`hosted/`) — el que se usa a diario

### El concepto

En vez de ejecutar el agente una vez, lo **expones detrás de un servidor
HTTP** que Foundry sabe invocar. La pieza clave es:

```python
from agent_framework.devui import serve
serve(entities=[agente], port=8080)
```

`serve(...)` levanta un servidor (basado en FastAPI/uvicorn) que implementa el
protocolo "Responses" — el mismo formato que usa la API de Respuestas de
OpenAI. Este es exactamente el mecanismo que usa `azd ai agent run` cuando
corres un agente Python localmente antes de desplegarlo: mismo protocolo,
mismo puerto por defecto (8080/8088 según la herramienta).

### Archivos

- [main.py](hosted/main.py) — el agente, expuesto con `serve(...)` en vez de
  llamarlo directamente. Explica en sus comentarios cada diferencia frente a
  la versión autoalojada.
- [azure.yaml.ejemplo](hosted/azure.yaml.ejemplo) — cómo se vería el archivo
  que `azd ai agent init` generaría para amarrar este código a un proyecto
  real de Foundry (**solo de referencia**, no es funcional por sí solo).
- [.env](hosted/.env) / [requirements.txt](hosted/requirements.txt)

### Paso 1 — Probarlo localmente (sin tocar Azure todavía)

1. Completa `hosted/.env` con tu `PROJECT_ENDPOINT` y `MODEL_DEPLOYMENT_NAME`
   (los mismos del lab09).
2. Activa el venv de la raíz e inicia sesión: `az login`.
3. Ejecuta:
   ```bash
   cd lab10/hosted
   python main.py
   ```
4. Abre `http://127.0.0.1:8080` en el navegador: verás el **Agent Inspector**,
   una UI de prueba donde puedes chatear con el agente igual que harías en el
   portal de Foundry — pero corriendo 100% en tu máquina.

> Esto es equivalente conceptualmente a lo que hace `azd ai agent run
> --no-client` sobre un proyecto scaffoldeado con `azd ai agent init`: mismo
> protocolo, mismo tipo de servidor.

### Paso 2 — Cómo se publica de verdad como Hosted Agent (con `azd`)

Esto **no lo ejecutamos** en este laboratorio (requiere recursos reales de
Azure), pero así es el flujo día a día en un equipo que usa Foundry en
producción:

1. **Prerrequisitos**: tener `azd` instalado, y haber hecho `az login` +
   `azd auth login`.
2. **Scaffold** (si empezaras desde cero): `azd ai agent init` — genera la
   estructura `azure.yaml` + `src/<agente>/main.py` (lo que ya armamos a mano
   en esta carpeta, para que entiendas la forma).
3. **Personalizar**: editar `main.py` con tu lógica real de negocio (tools,
   instrucciones) — igual que hicimos con `consultar_disponibilidad`.
4. **Probar localmente**: `azd ai agent run --no-client` levanta el mismo
   servidor que viste en el Paso 1, y `azd ai agent invoke --local "..."` te
   deja mandarle mensajes desde la terminal.
5. **Provisionar infraestructura** (una vez por entorno): `azd provision` —
   crea (o reutiliza) el proyecto de Foundry, el deployment del modelo, y la
   infraestructura de hosting (Container Apps/Registry por debajo).
6. **Desplegar**: `azd deploy` — construye la imagen con tu código y la
   publica como una **nueva versión** del agente dentro de tu proyecto de
   Foundry. A partir de aquí, el agente SÍ aparece en el portal, con su
   propio endpoint invocable.
7. **Invocar en remoto**: `azd ai agent invoke "..."` — ahora habla con la
   versión desplegada en Azure, no con tu máquina.
8. **Iterar**: cambias código → `azd deploy` de nuevo → nueva versión, sin
   tocar infraestructura ni URLs.

### Por qué esto SÍ es el camino recomendado para producción

- El agente es una entidad real dentro de Foundry: versionado automático,
  rollback fácil, invocación remota administrada.
- Logs, trazas y evaluación (calidad de respuestas) vienen integrados sin
  configurar nada extra.
- La infraestructura (contenedores, registro, red) la gestiona `azd`/Foundry
  por ti — no reinventas el hosting.
- Autenticación de producción con identidad administrada, gestionada por el
  mismo flujo de `azd provision`.

## Resumen para recordar

- **Autoalojado** = "es un script que corro donde sea" → rápido para
  prototipos, pero Foundry no lo conoce como agente.
- **Hosted** = "Foundry sabe que esto es un agente, con versiones, logs y un
  endpoint propio" → **esto es lo que se usa día a día en producción.**
- El código del agente en sí (`Agent`, `@tool`, `FoundryChatClient`) es
  prácticamente el mismo en los dos casos — lo que cambia es cómo lo expones
  al final (`agente.run(...)` una vez, vs. `serve(entities=[agente])` como
  servidor persistente).
