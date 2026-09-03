# Imagen mínima para "autoalojar" el agente en cualquier lugar
# (Azure Container Apps, App Service for Containers, una VM, etc.)
#
# Esto es solo ILUSTRATIVO: muestra la forma/estructura del despliegue,
# no un pipeline de producción completo (falta manejo de secretos vía
# Key Vault, health checks, multi-stage build, etc.)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agente_autoalojado.py .

# En un despliegue real, PROJECT_ENDPOINT/MODEL_DEPLOYMENT_NAME se inyectan
# como variables de entorno del contenedor (no con un archivo .env dentro
# de la imagen), y la autenticación normalmente sería con una Managed
# Identity en vez de AzureCliCredential (que depende de "az login" local).
CMD ["python", "agente_autoalojado.py"]
