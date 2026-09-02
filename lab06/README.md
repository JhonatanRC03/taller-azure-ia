# Lab06 - Agente con funciones personalizadas (custom function tools)

Adaptación en español del laboratorio de Microsoft Learn **"Use a custom function in an AI agent"**,
usando el mismo estilo de conexión que el resto del repositorio (`openai.OpenAI` + `.env` en la raíz),
en lugar de `azure-ai-projects` + `az login`.

## Archivos

- **`funciones.py`**: las funciones "reales" que el agente puede invocar como herramientas:
  - `proximo_evento_visible(ubicacion)`: busca el próximo evento astronómico visible desde un continente.
  - `calcular_costo_observacion(nivel_telescopio, horas, prioridad)`: calcula el costo de alquilar un telescopio.
  - `generar_reporte_observacion(...)`: genera un archivo `.txt` con el resumen de la observación.
- **`agente.py`**: el agente conversacional. Define el esquema JSON de cada función (`function tools`),
  envía el mensaje del usuario al modelo, detecta si pide ejecutar una función, la ejecuta en Python
  y devuelve el resultado al modelo para obtener la respuesta final.

## Cómo funciona (resumen del concepto)

1. Le decimos al modelo qué funciones existen y cómo se llaman sus parámetros (JSON Schema), pero
   **nunca le damos el código**: el modelo solo puede "pedir" que se ejecuten.
2. Si el modelo decide usar una función, la respuesta trae un bloque `function_call` con el nombre
   de la función y los argumentos en JSON.
3. Nuestro script ejecuta la función de verdad en Python y agrega el resultado al historial como
   `function_call_output`.
4. Se vuelve a llamar al modelo con ese resultado para que redacte la respuesta final en lenguaje natural.

## Cómo ejecutarlo

Desde la carpeta `lab06` (con el entorno virtual del repo activado y `requirements.txt` instalado):

```bash
python agente.py
```

Prueba con algo como:

```
Encuentra el próximo evento que pueda ver desde america_del_sur y dime el costo de 5 horas de telescopio premium con prioridad normal.
```

Y luego, como seguimiento:

```
Genera esa información en un reporte para el Observatorio Bellows.
```

Verás que se crea un archivo `reporte-<evento>.txt` en esta misma carpeta con el resumen.

Escribe `salir` para terminar la conversación.
