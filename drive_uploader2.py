import os
import json
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime

def upload_to_drive2(file_stream: BytesIO, filename: str):
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

    

    # Preparar el archivo para subir
    file_metadata = {'name': filename}
    media = MediaIoBaseUpload(
        file_stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # Subir archivo
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink, webContentLink'
    ).execute()

    # 🔓 Hacerlo público
    permission = {
        'type': 'anyone',
        'role': 'reader',
    }
    service.permissions().create(
        fileId=file['id'],
        body=permission
    ).execute()

    # Retorna enlace para ver y descargar el archivo
    return file.get('webViewLink'), file.get('webContentLink')
