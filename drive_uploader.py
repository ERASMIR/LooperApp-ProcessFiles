import os
import json
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from datetime import datetime
import logging

def upload_to_drive(file_stream: BytesIO, filename: str):
    # Leer las credenciales desde la variable de entorno
    credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise RuntimeError("La variable de entorno GOOGLE_CREDENTIALS_JSON no está configurada.")

    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )

    # Inicializar el cliente de Google Drive
    service = build('drive', 'v3', credentials=credentials)

    # Asegurarse de que el stream está al inicio
    file_stream.seek(0)

    # Generar nombre único con fecha y hora
    fecha_actual = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nombre_archivo = f"{filename}_{fecha_actual}.xlsx"

    # ✅ Especificar carpeta compartida como destino
    #folder_id = "151RwOhsFmbYqztH9lfTuyLXr1PXldIZV"

    FOLDER_ID = '151RwOhsFmbYqztH9lfTuyLXr1PXldIZV'  # tu Drive compartido

    # Preparar el archivo para subir
    file_metadata = {
        'name': nombre_archivo,
        #'parents': [folder_id]  # 👈 Este campo asegura que se suba a la carpeta compartida
        'parents': [FOLDER_ID]
    
    }

    #file_metadata =     
    #{'name': nombre_archivo}

    
    media = MediaIoBaseUpload(
        file_stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # Subir archivo
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink, webContentLink',
        supportsAllDrives=True
    ).execute()

    # Intentar hacer público el archivo, pero manejar errores de permisos heredados
    try:
        service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'},
            supportsAllDrives=True
        ).execute()
    except HttpError as e:
        if e.resp.status == 403 and "cannotModifyInheritedPermission" in str(e):
            logging.warning("⚠️ El archivo hereda permisos y no se puede hacer público directamente.")
        else:
            raise  # Si es otro error, lanzar excepción



    #Hacer público el archivo
    #service.permissions().create(
        #fileId=file['id'],
        #body={'type': 'anyone', 'role': 'reader'},
        #supportsAllDrives=True
    #).execute()

    # Retornar ambos enlaces: vista (web) y descarga (directo)
    view_url = file.get('webViewLink')
    download_url = file.get('webContentLink')

    return view_url, download_url
