import pandas as pd
import os
from io import BytesIO
import base64
from drive_uploader import upload_to_drive
#from .drive_uploader import upload_to_drive  # ya lo tienes importado

def process_files2(matrix_bytes, sales_bytes) -> dict:
    try:
        print("Iniciando procesamiento de archivos...")

        matrix_data = get_file_data2(BytesIO(matrix_bytes))
        sales_data = get_file_data2(BytesIO(sales_bytes))

        print("Generando reporte...")
        report, log_info = generate_report2(matrix_data, sales_data)
        output = save_report_to_memory2(report)

        print("Subiendo archivo a Google Drive...")
        output.seek(0)
        file_name = "reporte_generado.xlsx"
        
        drive_url = upload_to_drive(output, file_name)

        print("✅ Subida exitosa. URL:", drive_url)
        print_logs2(log_info)

        print("📤 Resultado final:", {
            "drive_url": drive_url,
            "log_summary": log_info,
            "sumadores": report
        })

        return {
            "drive_url": drive_url,
            "log_summary": log_info,  # 🔁 Esto estará disponible en tu Azure Function
            "sumadores": report
        }

    except Exception as error:
        print("Error:", error)
        raise RuntimeError("No se pudo procesar los archivos.") from error

    

def get_file_data2(file_like_obj):
    """Lee y parsea un archivo Excel desde un objeto de tipo BytesIO."""
    df = pd.read_excel(file_like_obj, dtype=str)
    print(f"columnas del archivo: {df.columns.tolist()}")
    df = df.map(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
    return df.to_dict(orient='records')



def save_report_to_memory2(report2):
    """Guarda el reporte en un objeto BytesIO y lo retorna."""
    df = pd.DataFrame(report2)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output



def generate_report2(matrix_data, sales_data):
    """Genera un reporte sumando toneladas de materiales por categoría, considerando unidad de venta."""

    sumadores = initialize_sumadores2()
    print(f"Procesando {len(sales_data)} registros de ventas...")

    total_lines = len(sales_data)
    processed_correctly = 0
    not_found_entries = []

    for index, sale in enumerate(sales_data, start=1):
        producto_venta = str(sale.get('Descripción del producto', '')).strip()
        unidad_venta = str(sale.get('Unidad de venta', '')).strip().lower()
        cantidad_vendida = to_float2(sale.get('Cantidad', 0))

        if cantidad_vendida <= 0:
            print(f"Línea {index}: Cantidad <= 0, se omite. Producto: {producto_venta}, Unidad: {unidad_venta}")
            continue

        # Buscar coincidencia exacta en matriz: por descripción Y unidad
        matching_items = [
            item for item in matrix_data
            if item.get('Descripción del producto', '').strip() == producto_venta and
               item.get('Unidad de venta', '').strip().lower() == unidad_venta
        ]

        if not matching_items:
            print(f"Línea {index}: No se encontró correspondencia para producto y unidad: {producto_venta} - {unidad_venta}")
            #not_found_entries.append((index, producto_venta, unidad_venta))
            not_found_entries.append({
                "Línea del Registro de Ventas": index,
                "SKU": producto_venta,
                "Unidad de venta": unidad_venta
            })
            continue

        processed_correctly += 1

        for item in matching_items:
            material = item.get('Materiales', '').strip()
            categoria = item.get('Categoría', '').strip().lower()
            categoria_raw = item.get('Categoría', '')
            #categoria = categoria_raw.strip().lower().replace('á', 'a')
            peso_por_unidad = to_float2(item.get('TON', 0))

            if not material or peso_por_unidad <= 0:
                print(f"Línea {index}: Material o peso inválido. Producto: {producto_venta}")
                continue

            peso_total = round(peso_por_unidad * cantidad_vendida, 8)
            print(f"Línea {index}: Material = {material}, Categoría = {categoria}, Peso Total = {peso_total}")

            if 'no domiciliario' in categoria:
                add_to_sumadores2(sumadores['no domiciliario'], material, peso_total)
            elif 'domiciliario' in categoria:
                add_to_sumadores2(sumadores['domiciliario'], material, peso_total)
            else:
                print(f"Línea {index}: Categoría desconocida '{categoria_raw}' para producto {producto_venta}")


            #if categoria == 'domiciliario':
                #add_to_sumadores2(sumadores['domiciliario'], material, peso_total)
            #elif categoria == 'no domiciliario':
                #add_to_sumadores2(sumadores['no domiciliario'], material, peso_total)

    # Logs finales
    log_info = {
        "total_lines": total_lines,
        "processed_correctly": processed_correctly,
        "not_found_entries": not_found_entries
    }
    return format_report2(sumadores), log_info




def print_logs2(log_info):
    """Imprime los logs finales del procesamiento."""
    total_lines = log_info["total_lines"]
    processed_correctly = log_info["processed_correctly"]
    not_found_skus = log_info["not_found_entries"]

    print("\n Resumen del procesamiento:")
    print(f"• Total de líneas procesadas: {total_lines}")
    print(f"• Líneas procesadas correctamente: {processed_correctly}")
    print(f"• Líneas no procesadas (SKU no encontrado): {len(not_found_skus)}")
    if not_found_skus:
        print("• Detalles de SKUs no encontrados:")
        for line, sku, unidad in not_found_skus:
            print(f"  - Línea {line}: SKU: {sku}, Unidad: {unidad}")



def to_float2(value):
    """Convierte valores a float de forma segura."""
    try:
        if value is None or str(value).strip() == '':
            print(f" Valor nulo o vacío detectado: {value}")
            return 0.0
        return round(float(str(value).replace(',', '.')), 8)
    except ValueError as e:
        print(f" Error al convertir a float: {value}, Error: {e}")
        return 0.0

def initialize_sumadores2():
    """Inicializa los sumadores de materiales diferenciando por categoría: domiciliario y no domiciliario."""

    materials_domiciliario = [
        "Aluminio (latas)", 
        "Hojalata", 
        "Metal con aire comprimido",
        "Otros envases de metal", 
        "Metales Reutilizables Nuevos", 
        "Metales Reutilizables Recuperados",
        "Metales Reutilizables convertidos en Residuos", 
        
        "Plástico compostable",
        "Botellas PET (1)",
        "Otros envases PET (1)", 
        "Plásticos Reutilizables Nuevos", 
        "Plásticos Reutilizables Recuperados",
        "Plásticos Reutilizables convertidos en Residuos", 

        "Envases de PEAD que NO contienen sustancias con grasa (2) (Flexible)",
        "Envases de PEAD que contienen sustancias con grasa (2) (Flexible)",
        "PVC (3) (Flexible)",
        "Envases de PEBD que NO contienen sustancias con grasa (4) (Flexible)",
        "Envases de PEBD que contienen sustancias con grasa (4) (Flexible)",
        "Envases de PP que NO contienen sustancias con grasa (5) (Flexible)",
        "Envases de PP que contienen sustancias con grasa (5) (Flexible)",
        "Envases de PS que NO contienen sustancias con grasa (6) (Flexible)",
        "Envases de PS que contienen sustancias con grasa (6) y envases de EPS (Flexible)",
        "Otros (7) (Flexible)",
       
        "Envases de PEAD que NO contienen sustancias con grasa (2) (Rígido)",
        "Envases de PEAD que contienen sustancias con grasa (2) (Rígido)",
        "PVC (3) (Rígido)", 
        "Envases de PEBD que NO contienen sustancias con grasa (4) (Rígido)",
        "Envases de PEBD que contienen sustancias con grasa (4) (Rígido)",
        "Envases de PP que NO contienen sustancias con grasa (5) (Rígido)",
        "Envases de PP que contienen sustancias con grasa (5) (Rígido)",
        "Envases de PS que NO contienen sustancias con grasa (6) (Rígido)",        
        "Envases de PS que contienen sustancias con grasa (6) y envases de EPS (Rígido)",
        "Otros (7) (Rígido)",
        
        "Cartón", 
        "Papel", 
        "Otro papel compuesto",
        "Papeles y Cartones Reutilizables Nuevos",
        "Papeles y Cartones Reutilizables Recuperados",
        "Papeles y Cartones Reutilizables convertidos en Residuos",

        "Cartón para bebidas (Tetrapack)",
        "Vidrio",
        "Vidrio Reutilizables Nuevos",
        "Vidrio Reutilizables Recuperados",
        "Vidrio Reutilizables convertidos en Residuos",
             
        "Madera",
        "Otros Reutilizables Nuevos",
        "Otros Reutilizables Recuperados",
        "Otros Reutilizables convertidos en Residuos",
        "Otros no Madera"
    ]

    materials_no_domiciliario = [
        "Envases de Aluminio",
        "Hojalata", 
        "Metal con aire comprimido",
        "Envases metálicos de otros metales", 
        "Metales Reutilizables Nuevos",
        "Metales Reutilizables Recuperados",
        "Metales Reutilizables convertidos en Residuos",

        "Plástico compostable",      
        "Envases PET",
        "Plásticos Reutilizables Nuevos",
        "Plásticos Reutilizables Recuperados",
        "Plásticos Reutilizables convertidos en Residuos",

        "Envases de PEAD que NO contienen sustancias con grasa (2) (Flexible)",
        "Envases de PEAD que contienen sustancias con grasa (2) (Flexible)",
        "PVC (3) (Flexible)",
        "Envases de PEBD que NO contienen sustancias con grasa (4) (Flexible)",
        "Envases de PEBD que contienen sustancias con grasa (4) (Flexible)",
        "Envases de PP que NO contienen sustancias con grasa (5) (Flexible)",
        "Envases de PP que contienen sustancias con grasa (5) (Flexible)",
        "Envases de PS que NO contienen sustancias con grasa (6) (Flexible)",
        "Envases de PS que contienen sustancias con grasa (6) y envases de EPS (Flexible)",
        "Otros (7) (Flexible)",

        "Envases de PEAD que NO contienen sustancias con grasa (2) (Rígido)",       
        "Envases de PEAD que contienen sustancias con grasa (2) (Rígido)",         
        "PVC (3) (Rígido)",         
        "Envases de PEBD que NO contienen sustancias con grasa (4) (Rígido)",     
        "Envases de PEBD que contienen sustancias con grasa (4) (Rígido)",        
        "Envases de PP que NO contienen sustancias con grasa (5) (Rígido)",
        "Envases de PP que contienen sustancias con grasa (5) (Rígido)",        
        "Envases de PS que NO contienen sustancias con grasa (6) (Rígido)",        
        "Envases de PS que contienen sustancias con grasa (6) y envases de EPS (Rígido)",
        "Otros (7) (Rígido)",

        "Cartón", 
        "Papel", 
        "Otro papel compuesto", 
        "Papeles y Cartones Reutilizables Nuevos",
        "Papeles y Cartones Reutilizables Recuperados",
        "Papeles y Cartones Reutilizables convertidos en Residuos",

        "Madera",
        "Otros Reutilizables Nuevos",
        "Otros Reutilizables Recuperados",
        "Otros Reutilizables convertidos en Residuos",
        "Otros no Madera"
    ]

    return {
        "domiciliario": create_sumadores2(materials_domiciliario),
        "no domiciliario": create_sumadores2(materials_no_domiciliario),
    }


def create_sumadores2(materials):
    """Crea un diccionario con sumadores inicializados en 0."""
    return {material: 0.0 for material in materials}


def add_to_sumadores2(sumadores, material, peso):
    """Agrega valores al sumador correspondiente."""
    if material in sumadores:
        sumadores[material] += peso


def format_report2(sumadores):
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



def save_report_to_base642(report):
    """Convierte el reporte a un archivo Excel y lo retorna codificado en base64."""
    df = pd.DataFrame(report)

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    base64_file = base64.b64encode(output.read()).decode('utf-8')
    print("✅ Reporte generado en base64 correctamente.")
    
    return base64_file


