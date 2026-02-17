# LooperApp ProcessFiles — Agent Context

## Proyecto
- **Tipo:** Azure Function App (Python 3.11)
- **Azure URL:** https://looperapp.azurewebsites.net
- **GitHub:** https://github.com/ERASMIR/LooperApp-ProcessFiles (branch: main)
- **Puerto local:** 7075 (`func start --port 7075`)
- **Version tag:** v1.0-deploy-2026-02-16

## Arquitectura
```
LooperApp-ProcessFiles/
├── function_app.py              # Entry point, registra 4 rutas HTTP
├── LooperProcesFile.py          # Procesamiento v1 (legacy)
├── LooperProcesFiles2.py        # Procesamiento v2 (legacy)
├── LooperProcesFiles3.py        # Procesamiento v3 (legacy)
├── LooperProcesFiles4.py        # Procesamiento v4 (version activa)
├── drive_uploader.py            # Subir a Google Drive v1
├── drive_uploader2.py           # Subir a Google Drive v2
├── materiales.json              # Catalogo de materiales por GRANSIC (1=ReSimple, 2=PROREP)
├── materiales.txt               # Referencia de materiales en texto
├── requirements.txt             # Dependencias Python
├── host.json                    # Config Azure Functions
└── local.settings.json          # Env vars locales (gitignored)
```

## Endpoints (4 funciones)
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| POST | /api/LooperProcesFiles | Procesamiento v1 (legacy) |
| POST | /api/LooperProcesFiles2 | Procesamiento v2 (legacy) |
| POST | /api/LooperProcesFiles3 | Procesamiento v3 (legacy) |
| POST | /api/LooperProcesFiles4 | Procesamiento v4 (EN USO) |

## Logica de procesamiento (v4)
- Recibe archivos Excel (matriz de materiales + registro de ventas) como base64 o URLs
- Descarga archivos, lee con openpyxl/pandas
- Cruza datos de ventas con matriz de materiales
- Clasifica segun catalogo GRANSIC (materiales.json):
  - **GRANSIC 1 (ReSimple):** categorias peligrosos/no_peligrosos
  - **GRANSIC 2 (PROREP):** categorias reciclable/no_reciclable
- Genera reporte JSON con totales por material y categoria
- Sube reporte a Google Drive
- Retorna JSON con resultados y URLs de descarga

## Catalogo GRANSIC (materiales.json)
- ID 1 = ReSimple: tiene peligrosidad (peligrosos / no peligrosos)
- ID 2 = PROREP: tiene reciclabilidad (reciclable / no reciclable)
- Cada GRANSIC define sus propias listas de materiales

## Variables de entorno
- GOOGLE_CREDENTIALS_JSON (service account para Google Drive)
- FUNCTIONS_WORKER_RUNTIME = "python"

## Dependencias Python (requirements.txt)
- azure-functions, openpyxl, pandas, google-auth, google-api-python-client, requests

## Deploy
```bash
func azure functionapp publish looperapp
```
- Nota: Azure usa Python 3.11; local puede ser 3.12 (compatible)
