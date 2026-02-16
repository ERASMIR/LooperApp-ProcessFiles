import azure.functions as func
import logging
from io import BytesIO
import json
import requests
import base64
from LooperProcesFile import process_files
from LooperProcesFiles2 import process_files2
from LooperProcesFiles3 import process_files3
from LooperProcesFiles4 import process_files4
from google.oauth2 import service_account
import os
from azure.functions import HttpRequest, HttpResponse
from azure.functions.decorators import FunctionApp

from azure.functions import AuthLevel
app = FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)


@app.route(route="LooperProcesFiles", auth_level=func.AuthLevel.ANONYMOUS)
def LooperProcesFile(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('✅ [INICIO] Conexión establecida con Azure Function.')

    try:
        # 📥 Leer body
        body = req.get_json()
        logging.info(f"📦 Body recibido: {body}")

        matrix_path = body.get("matrixUrl")
        sales_path = body.get("salesUrl")

        if not matrix_path or not sales_path:
            logging.warning("⚠️ Faltan URLs de archivos en el request.")
            return func.HttpResponse("Faltan URLs de archivos.", status_code=400)

        logging.info(f"🔗 URLs recibidas:\n- Matrix: {matrix_path}\n- Sales: {sales_path}")

        # 🌐 Descargar archivos
        matrix_resp = requests.get(matrix_path)
        sales_resp = requests.get(sales_path)

        if matrix_resp.status_code != 200:
            logging.error(f"❌ Error al descargar matrix file. Código: {matrix_resp.status_code}")
            return func.HttpResponse("Error al descargar el archivo de matriz.", status_code=500)

        if sales_resp.status_code != 200:
            logging.error(f"❌ Error al descargar sales file. Código: {sales_resp.status_code}")
            return func.HttpResponse("Error al descargar el archivo de ventas.", status_code=500)

        logging.info("📥 Archivos descargados correctamente.")

        # 🔐 Cargar credenciales desde variable de entorno
        credenciales_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not credenciales_json:
            logging.error("❌ Variable de entorno GOOGLE_CREDENTIALS_JSON no encontrada.")
            return func.HttpResponse("No se encontró la variable GOOGLE_CREDENTIALS_JSON", status_code=500)

        logging.info("🔐 Credenciales cargadas, procesando archivo JSON...")

        credentials_info = json.loads(credenciales_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        logging.info("✅ Credenciales de Google cargadas correctamente.")

        # 🛠️ Procesar archivos y subir a Drive
        logging.info("🧪 Iniciando procesamiento de archivos...")
        drive_url = process_files(matrix_resp.content, sales_resp.content, credentials)

        if not drive_url:
            logging.error("❌ No se recibió URL del archivo procesado.")
            return func.HttpResponse("Error durante el procesamiento o subida a Drive.", status_code=500)

        logging.info(f"✅ Archivo subido a Google Drive exitosamente. URL: {drive_url}")

        # 🚀 Devolver respuesta al frontend
        return func.HttpResponse(
            json.dumps({
                "fileUrl": drive_url
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error("❌ Excepción general durante el procesamiento:", exc_info=True)
        return func.HttpResponse(
            body=f"Error interno del servidor: {str(e)}",
            status_code=500
        )



#ESTA ESTA EN OPERACION, LA OTRA NO
#@app.function_name(name="LooperProcesFiles2") ESTA ESTA EN OPERACION, LA OTRA NO
@app.route(route="LooperProcesFiles2", auth_level=func.AuthLevel.ANONYMOUS)
def LooperProcesFile2(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('✅ [INICIO] Conexión establecida con Azure Function.')

    try:
        # 📥 Leer body
        body = req.get_json()
        logging.info(f"📦 Body recibido: {body}")

        # ✅ Validar que el body sea un diccionario
        if not isinstance(body, dict):
            return func.HttpResponse("❌ El cuerpo del request no es un JSON válido.", status_code=400)

        matrix_path = body.get("matrixUrl")
        sales_path = body.get("salesUrl")

        if not matrix_path or not sales_path:
            logging.warning("⚠️ Faltan URLs de archivos en el request.")
            return func.HttpResponse("Faltan URLs de archivos.", status_code=400)

        # 🌐 Descargar archivos
        matrix_resp = requests.get(matrix_path)
        sales_resp = requests.get(sales_path)

        if matrix_resp.status_code != 200 or sales_resp.status_code != 200:
            return func.HttpResponse("Error al descargar uno o ambos archivos.", status_code=500)

        # 🔐 Cargar credenciales
        credenciales_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not credenciales_json:
            return func.HttpResponse("No se encontró la variable GOOGLE_CREDENTIALS_JSON", status_code=500)

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credenciales_json),
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        logging.info(f"📥 matrix_resp.content: {type(matrix_resp.content)}")
        logging.info(f"📥 sales_resp.content: {type(sales_resp.content)}")


        # 🛠️ Procesar archivos
        result = process_files2(matrix_resp.content, sales_resp.content)

        if not result or not result.get("drive_url"):
            return func.HttpResponse("Error durante el procesamiento o subida a Drive.", status_code=500)

        logging.info(f"📝 Resultado del procesamiento: {result}")
        #result = process_files2(matrix_resp.content, sales_resp.content)

        # 🔍 Verificar qué devuelve realmente
        logging.info(f"🔎 Tipo de result: {type(result)}")
        logging.info(f"📦 Contenido de result: {result}")


        # 🔄 Renombrar claves para respuesta al frontend
        log_summary = result["log_summary"]
        log_summary_es = {
            "Total de líneas procesadas": log_summary.get("total_lines", 0),
            "Líneas procesadas correctamente": log_summary.get("processed_correctly", 0),
            "Registros no encontrados en Matriz de Materiales": log_summary.get("not_found_entries", [])
        }

        sumadores = {}
        try:
            sumadores = result.get("sumadores", {})
        except AttributeError:
            # result no tiene método get
            if isinstance(result, dict) and "sumadores" in result:
                sumadores = result["sumadores"]
            else:
                sumadores = {}


        # 🚀 Devolver respuesta
        return func.HttpResponse(
            json.dumps({
                "fileUrl": result["drive_url"],
                "logSummary": log_summary_es,
                "sumadores": sumadores  # Aquí envías el JSON con los resultados
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error("❌ Excepción general durante el procesamiento:", exc_info=True)
        return func.HttpResponse(
            body=f"Error interno del servidor: {str(e)}",
            status_code=500
        )


#@app.function_name(name="LooperProcesFiles2") ESTA ESTA EN OPERACION, LA OTRA NO
@app.route(route="LooperProcesFiles3", auth_level=func.AuthLevel.ANONYMOUS)
def LooperProcesFile3(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('✅ [INICIO] Conexión establecida con Azure Function.')

    try:
        # 📥 Leer body
        body = req.get_json()
        logging.info(f"📦 Body recibido: {body}")

        # ✅ Validar que el body sea un diccionario
        if not isinstance(body, dict):
            return func.HttpResponse("❌ El cuerpo del request no es un JSON válido.", status_code=400)

        matrix_path = body.get("matrixUrl")
        sales_path = body.get("salesUrl")

        if not matrix_path or not sales_path:
            logging.warning("⚠️ Faltan URLs de archivos en el request.")
            return func.HttpResponse("Faltan URLs de archivos.", status_code=400)

        # 🌐 Descargar archivos
        matrix_resp = requests.get(matrix_path)
        sales_resp = requests.get(sales_path)

        if matrix_resp.status_code != 200 or sales_resp.status_code != 200:
            return func.HttpResponse("Error al descargar uno o ambos archivos.", status_code=500)

        # 🔐 Cargar credenciales
        credenciales_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not credenciales_json:
            return func.HttpResponse("No se encontró la variable GOOGLE_CREDENTIALS_JSON", status_code=500)

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credenciales_json),
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        logging.info(f"📥 matrix_resp.content: {type(matrix_resp.content)}")
        logging.info(f"📥 sales_resp.content: {type(sales_resp.content)}")


        # 🛠️ Procesar archivos
        result = process_files3(matrix_resp.content, sales_resp.content)

        if not result or not result.get("drive_url"):
            return func.HttpResponse("Error durante el procesamiento o subida a Drive.", status_code=500)

        logging.info(f"📝 Resultado del procesamiento: {result}")
        #result = process_files2(matrix_resp.content, sales_resp.content)

        # 🔍 Verificar qué devuelve realmente
        logging.info(f"🔎 Tipo de result: {type(result)}")
        logging.info(f"📦 Contenido de result: {result}")


        # 🔄 Renombrar claves para respuesta al frontend
        log_summary = result["log_summary"]
        log_summary_es = {
            "Total de líneas procesadas": log_summary.get("total_lines", 0),
            "Líneas procesadas correctamente": log_summary.get("processed_correctly", 0),
            "Registros no encontrados en Matriz de Materiales": log_summary.get("not_found_entries", [])
        }

        sumadores = {}
        try:
            sumadores = result.get("sumadores", {})
        except AttributeError:
            # result no tiene método get
            if isinstance(result, dict) and "sumadores" in result:
                sumadores = result["sumadores"]
            else:
                sumadores = {}


        # 🚀 Devolver respuesta
        return func.HttpResponse(
            json.dumps({
                "fileUrl": result["drive_url"],
                "logSummary": log_summary_es,
                "sumadores": sumadores  # Aquí envías el JSON con los resultados
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error("❌ Excepción general durante el procesamiento (v3):", exc_info=True)
        return func.HttpResponse(
            body=f"Error interno del servidor: {str(e)}",
            status_code=500
        )


@app.route(route="LooperProcesFiles4", auth_level=func.AuthLevel.ANONYMOUS)
def LooperProcesFile4(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('✅ [INICIO] Conexión establecida con Azure Function (v4).')

    try:
        body = req.get_json()
        logging.info(f"📦 Body recibido: {body}")

        if not isinstance(body, dict):
            return func.HttpResponse("❌ El cuerpo del request no es un JSON válido.", status_code=400)

        matrix_path = body.get("matrixUrl")
        sales_path = body.get("salesUrl")
        gransic_id = body.get("gransic_id")

        if not matrix_path or not sales_path:
            logging.warning("⚠️ Faltan URLs de archivos en el request.")
            return func.HttpResponse("Faltan URLs de archivos.", status_code=400)

        if not gransic_id:
            logging.warning("⚠️ Falta gransic_id en el request.")
            return func.HttpResponse("Falta gransic_id en el request.", status_code=400)

        matrix_resp = requests.get(matrix_path)
        sales_resp = requests.get(sales_path)

        if matrix_resp.status_code != 200 or sales_resp.status_code != 200:
            return func.HttpResponse("Error al descargar uno o ambos archivos.", status_code=500)

        credenciales_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not credenciales_json:
            return func.HttpResponse("No se encontró la variable GOOGLE_CREDENTIALS_JSON", status_code=500)

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credenciales_json),
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        logging.info(f"📥 matrix_resp.content: {type(matrix_resp.content)}")
        logging.info(f"📥 sales_resp.content: {type(sales_resp.content)}")

        result = process_files4(matrix_resp.content, sales_resp.content, gransic_id)

        if not result or not result.get("drive_url"):
            return func.HttpResponse("Error durante el procesamiento o subida a Drive.", status_code=500)

        logging.info(f"📝 Resultado del procesamiento (v4): {result}")

        log_summary = result["log_summary"]
        log_summary_es = {
            "Total de líneas procesadas": log_summary.get("total_lines", 0),
            "Líneas procesadas correctamente": log_summary.get("processed_correctly", 0),
            "Registros no encontrados en Matriz de Materiales": log_summary.get("not_found_entries", [])
        }

        sumadores = {}
        try:
            sumadores = result.get("sumadores", {})
        except AttributeError:
            if isinstance(result, dict) and "sumadores" in result:
                sumadores = result["sumadores"]
            else:
                sumadores = {}

        return func.HttpResponse(
            json.dumps({
                "fileUrl": result["drive_url"],
                "logSummary": log_summary_es,
                "sumadores": sumadores
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error("❌ Excepción general durante el procesamiento (v4):", exc_info=True)
        return func.HttpResponse(
            body=f"Error interno del servidor: {str(e)}",
            status_code=500
        )