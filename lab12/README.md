# Lab 12 - Manejo de throttling (HTTP 429) en Azure OpenAI

Este laboratorio no viene de `mslearn-ai-agents`, sino que explora cómo
manejar el **throttling** (limitación de tasa) cuando un agente o
aplicación llama a un despliegue de Azure OpenAI y recibe **HTTP 429
(rate limit exceeded)** de forma intermitente, especialmente bajo carga.

## El problema: 429 (rate limit exceeded)

Un 429 significa que se superó el límite de **TPM/RPM** (tokens o requests
por minuto) asignado al despliegue. Azure OpenAI espera que el tráfico
esté distribuido de forma pareja en el tiempo; si se reintenta de
inmediato sin esperar, se genera más carga sobre un servicio que ya está
saturado, lo que empeora el problema (las llamadas fallidas igual cuentan
contra el límite por minuto).

## La estrategia: retry con backoff exponencial y jitter

La práctica recomendada por Microsoft Learn ("Rate limit best practices"
en el artículo de gestión de cuota de Azure OpenAI) es:

1. Esperar un retraso corto y aleatorio tras el primer fallo.
2. Si vuelve a fallar, **duplicar** el retraso (backoff exponencial).
3. Sumarle **jitter** (aleatoriedad) para que múltiples clientes no
   reintenten todos en el mismo instante exacto (evita el efecto "manada").
4. Limitar el número máximo de reintentos (p. ej. 5-10) para no reintentar
   infinitamente.
5. Si la respuesta 429 trae el header `retry-after-ms`, respetar ese valor
   en vez de tu propio cálculo.

Fuente: [Manage Azure OpenAI quota - Rate limit best practices](https://learn.microsoft.com/azure/ai-services/openai/how-to/quota)
y [Retry pattern - Azure Architecture Center](https://learn.microsoft.com/azure/architecture/patterns/retry).

## Contenido de este laboratorio

Ambos ejemplos usan la **Responses API** (`client.responses.create(...)`),
igual que [`chat/3_responses_api.py`](../chat/3_responses_api.py), en vez de
la Chat Completions API (más antigua). Los dos imprimen cada intento en
consola para que se vea el "dinamismo" del reintento en tiempo real.

- [`ejemplo_basico.py`](ejemplo_basico.py): la forma más simple de aplicar
  retry con backoff+jitter. El SDK de `openai` **ya implementa por dentro**
  backoff exponencial + jitter y respeta `retry-after-ms`
  (`openai._base_client._calculate_retry_timeout`), así que basta con subir
  `max_retries` (por defecto es 2) al crear el cliente:
  `OpenAI(..., max_retries=5)`. El script activa además el logger interno
  del SDK para mostrar en consola la línea `Retrying request to ... in X
  seconds` cada vez que el propio SDK reintenta un 429.
- [`ejemplo_produccion.py`](ejemplo_produccion.py): una versión con más
  control, usando la librería `tenacity` (agregada a `requirements.txt`),
  para casos donde no basta con la caja negra del SDK:
  - Reintenta **solo** ante `openai.RateLimitError` (429), no ante
    cualquier excepción.
  - Respeta el header `retry-after-ms` de la respuesta cuando está
    presente, en vez de inventar su propio retraso.
  - Agrega jitter aleatorio y backoff exponencial cuando no hay
    `retry-after-ms`.
  - Imprime cada intento (envío, 429 recibido, tiempo de espera elegido y
    su motivo) y además deja registro con `logging` para observabilidad
    en producción.
  - Deshabilita el retry interno del SDK (`max_retries=0`) para no
    duplicar reintentos (si se deja activo junto con `tenacity`, cada
    intento de `tenacity` podría disparar hasta 2 reintentos adicionales
    del SDK).

### Ejecutar

Ambos scripts reutilizan el `.env` de la raíz del repo
(`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`):

```bash
source .venv/bin/activate
python lab12/ejemplo_basico.py
python lab12/ejemplo_produccion.py
```
