import pandas as pd
import os
from io import BytesIO
import base64
from drive_uploader import upload_to_drive
#from .drive_uploader import upload_to_drive  # ya lo tienes importado

def process_files(matrix_bytes, sales_bytes, credentials) -> str:
    try:
        print("Iniciando procesamiento de archivos...")

        matrix_data = get_file_data(BytesIO(matrix_bytes))
        sales_data = get_file_data(BytesIO(sales_bytes))

        print("Generando reporte...")
        report, log_info = generate_report(matrix_data, sales_data)
        output = save_report_to_memory(report)

        print("Subiendo archivo a Google Drive...")
        output.seek(0)  # Asegurar que esté al inicio del archivo
        file_name = "reporte_generado.xlsx"
        
        # ✅ Usar la versión que recibe las credenciales
        drive_url = upload_to_drive(output, file_name)

        print("✅ Subida exitosa. URL:", drive_url)
        print_logs(log_info)

        return drive_url  # Devuelve el enlace

    except Exception as error:
        print("Error:", error)
        raise RuntimeError("No se pudo procesar los archivos.") from error
    
    

def get_file_data(file_like_obj):
    """Lee y parsea un archivo Excel desde un objeto de tipo BytesIO."""
    df = pd.read_excel(file_like_obj, dtype=str)
    print(f"columnas del archivo: {df.columns.tolist()}")
    df = df.map(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
    return df.to_dict(orient='records')



def save_report_to_memory(report):
    """Guarda el reporte en un objeto BytesIO y lo retorna."""
    df = pd.DataFrame(report)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output



def generate_report(matrix_data, sales_data):
    """Genera un reporte sumando toneladas de materiales por categoría."""
    unique_skus_sales = set(sale.get('Código producto (sku)', '').strip() for sale in sales_data)
    unique_skus_matrix = set(item.get('Descripción del producto', '').strip() for item in matrix_data)

    sumadores = initialize_sumadores()
    print(f"Procesando {len(sales_data)} registros de ventas...")

    # Contadores y logs
    total_lines = len(sales_data)
    processed_correctly = 0
    not_found_skus = []

    for index, sale in enumerate(sales_data, start=1):
        sku = str(sale.get('Producto', '')).strip()
        toneladas_vendidas = to_float(sale.get('CantidadReal', 0))
        unidad = str(sale.get('Unidad', '')).strip().lower()

        #print(f" Línea {index}: SKU: {sku}, Unidad: {unidad}, Cantidad inicial: {toneladas_vendidas}")

        # Aplicar factor según la unidad
        if unidad == "tambor":
            toneladas_vendidas *= 0.2
            print(f"Ajuste aplicado (tambor): Nueva cantidad = {toneladas_vendidas}")
        elif unidad == "litros":
            toneladas_vendidas /= 1000
            print(f"Ajuste aplicado (litros): Nueva cantidad = {toneladas_vendidas}")

        if toneladas_vendidas <= 0:
            print(f"Línea {index}: Cantidad <= 0 después del ajuste para SKU: {sku}")
            continue

        products = [item for item in matrix_data if item.get('Descripción del producto', '').strip() == sku]
        if not products:
            print(f"Línea {index}: No se encontraron productos para el SKU: {sku}")
            not_found_skus.append((index, sku))
            continue

        processed_correctly += 1
        for product in products:
            material = product.get('Materiales', '').strip()
            categoria = product.get('Categoría', '').strip().lower()
            peso_por_unidad = to_float(product.get('Peso (ton)', 0))
            print(f"Producto encontrado - Material: {material}, Categoría: {categoria}, Peso por unidad: {peso_por_unidad}")

            if not material or peso_por_unidad <= 0:
                print(f"Línea {index}: Material o peso inválido para SKU: {sku}")
                continue

            peso_total = round(peso_por_unidad * toneladas_vendidas, 8)
            if categoria == 'domiciliario':
                add_to_sumadores(sumadores['domiciliario'], material, peso_total)
            elif categoria == 'no domiciliario':
                add_to_sumadores(sumadores['no domiciliario'], material, peso_total)

    # Logs finales
    log_info = {
        "total_lines": total_lines,
        "processed_correctly": processed_correctly,
        "not_found_skus": not_found_skus
    }
    return format_report(sumadores), log_info




def print_logs(log_info):
    """Imprime los logs finales del procesamiento."""
    total_lines = log_info["total_lines"]
    processed_correctly = log_info["processed_correctly"]
    not_found_skus = log_info["not_found_skus"]

    print("\n Resumen del procesamiento:")
    print(f"• Total de líneas procesadas: {total_lines}")
    print(f"• Líneas procesadas correctamente: {processed_correctly}")
    print(f"• Líneas no procesadas (SKU no encontrado): {len(not_found_skus)}")
    if not_found_skus:
        print("• Detalles de SKUs no encontrados:")
        for line, sku in not_found_skus:
            print(f"  - Línea {line}: SKU: {sku}")


def to_float(value):
    """Convierte valores a float de forma segura."""
    try:
        if value is None or str(value).strip() == '':
            print(f" Valor nulo o vacío detectado: {value}")
            return 0.0
        return round(float(str(value).replace(',', '.')), 8)
    except ValueError as e:
        print(f" Error al convertir a float: {value}, Error: {e}")
        return 0.0


def initialize_sumadores():
    """Inicializa los sumadores de materiales."""
    materials = [
        "Envases de Aluminio", "Hojalata", "Metal con aire comprimido",
        "Envases metálicos de otros metales", "Cartón", "Papel", "Otro papel compuesto", "Madera",
        "Plástico compostable (Flexible)", "Plástico compostable (Rígido)", "Envases PET (Flexible)",
        "Envases PET (Rígido)", "Envases de PEAD que NO contienen sustancias con grasa (2) (Flexible)",
        "Envases de PEAD que NO contienen sustancias con grasa (2) (Rígido)",
        "Envases de PEAD que contienen sustancias con grasa (2) (Flexible)",
        "Envases de PEAD que contienen sustancias con grasa (2) (Rígido)",
        "PVC (3) (Flexible)", "PVC (3) (Rígido)", "Envases de PEBD que NO contienen sustancias con grasa (4) (Flexible)",
        "Envases de PEBD que NO contienen sustancias con grasa (4) (Rígido)",
        "Envases de PEBD que contienen sustancias con grasa (4) (Flexible)",
        "Envases de PEBD que contienen sustancias con grasa (4) (Rígido)",
        "Envases de PP que NO contienen sustancias con grasa (5) (Flexible)",
        "Envases de PP que NO contienen sustancias con grasa (5) (Rígido)",
        "Envases de PP que contienen sustancias con grasa (5) (Flexible)",
        "Envases de PP que contienen sustancias con grasa (5) (Rígido)",
        "Envases de PS que NO contienen sustancias con grasa (6) (Flexible)",
        "Envases de PS que NO contienen sustancias con grasa (6) (Rígido)",
        "Envases de PS que contienen sustancias con grasa (6) y envases de EPS (Flexible)",
        "Envases de PS que contienen sustancias con grasa (6) y envases de EPS (Rígido)",
        "Otros (7) (Flexible)", "Otros (7) (Rígido)"
    ]
    return {
        "domiciliario": create_sumadores(materials),
        "no domiciliario": create_sumadores(materials),
    }


def create_sumadores(materials):
    """Crea un diccionario con sumadores inicializados en 0."""
    return {material: 0.0 for material in materials}


def add_to_sumadores(sumadores, material, peso):
    """Agrega valores al sumador correspondiente."""
    if material in sumadores:
        sumadores[material] += peso


def format_report(sumadores):
    """Convierte sumadores en lista de diccionarios para exportar a CSV."""
    report = []
    for categoria, materiales in sumadores.items():
        for material, sumatoria_total in materiales.items():
            # Formatear el número con coma como separador decimal
            formatted_sumatoria = f"{sumatoria_total:.8f}".replace('.', ',')
            report.append({
                "categoría": categoria,
                "material": material,
                "sumatoria_total": formatted_sumatoria  # Valor formateado con coma
                #"sumatoria_total": f"{sumatoria_total:.8f}"
            })
    return report


#def save_report_to_csv(report, output_path):
    #"""Guarda el reporte generado en un archivo CSV."""
    #df = pd.DataFrame(report)
    #df.to_csv(output_path, sep=';', index=False, encoding='utf-8-sig')
    #df.to_excel(output_path, index=False, engine='openpyxl')  # Usar engine='openpyxl' para .xlsx
    #print(" Reporte guardado correctamente.")



def save_report_to_base64(report):
    """Convierte el reporte a un archivo Excel y lo retorna codificado en base64."""
    df = pd.DataFrame(report)

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    base64_file = base64.b64encode(output.read()).decode('utf-8')
    print("✅ Reporte generado en base64 correctamente.")
    
    return base64_file


