========================================
 LOOPERAPP-PROCESSFILES
 Azure Function App (Python)
========================================

Descripcion:
  Microservicio de procesamiento de archivos Excel (matriz de materiales
  y registro de ventas). Recibe archivos, los procesa con logica de negocio
  y retorna resultados estructurados en JSON.
  Desplegado en: https://looperapp.azurewebsites.net

Endpoints:
  POST   /api/LooperProcesFiles    - Procesamiento v1
  POST   /api/LooperProcesFiles2   - Procesamiento v2
  POST   /api/LooperProcesFiles3   - Procesamiento v3
  POST   /api/LooperProcesFiles4   - Procesamiento v4 (version actual en uso)

Archivos principales:
  function_app.py              - Entry point, registro de rutas HTTP
  LooperProcesFile.py          - Logica de procesamiento v1
  LooperProcesFiles2.py        - Logica de procesamiento v2
  LooperProcesFiles3.py        - Logica de procesamiento v3
  LooperProcesFiles4.py        - Logica de procesamiento v4 (activa)
  drive_uploader.py            - Utilidad para subir a Google Drive
  drive_uploader2.py           - Utilidad Drive v2

Variables de entorno requeridas:
  GOOGLE_SERVICE_ACCOUNT_JSON  - Credenciales de Google Drive (JSON)

Nota: Este proyecto usa Python 3.11 en Azure.
      La version local (3.12) puede diferir pero es compatible.

Version desplegada: v1.0-deploy-2026-02-16
Puerto local: 7075 (func start --port 7075)
