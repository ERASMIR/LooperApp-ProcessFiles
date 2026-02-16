import pandas as pd
import os
import json
from io import BytesIO
from drive_uploader import upload_to_drive


def process_files4(matrix_bytes, sales_bytes, gransic_id) -> dict:
    try:
        print("Iniciando procesamiento de archivos (v4)...")

        config = load_gransic_config(gransic_id)
        print(f"Config cargada para GRANSIC: {config['nombre']}")

        matrix_data = get_file_data2(BytesIO(matrix_bytes))
        sales_data = get_file_data2(BytesIO(sales_bytes))

        print("Generando reporte...")
        report, log_info = generate_report4(matrix_data, sales_data, config)
        output = save_report_to_memory2(report)

        print("Subiendo archivo a Google Drive...")
        output.seek(0)
        file_name = "reporte_generado.xlsx"

        drive_url = upload_to_drive(output, file_name)

        print("Subida exitosa. URL:", drive_url)
        print_logs2(log_info)

        return {
            "drive_url": drive_url,
            "log_summary": log_info,
            "sumadores": report
        }

    except Exception as error:
        print("Error:", error)
        raise RuntimeError("No se pudo procesar los archivos.") from error


def load_gransic_config(gransic_id):
    """Lee materiales.json y retorna la config del gransic_id solicitado."""
    config_path = os.path.join(os.path.dirname(__file__), 'materiales.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        all_config = json.load(f)

    gransic_key = str(gransic_id)
    if gransic_key not in all_config:
        raise ValueError(f"gransic_id '{gransic_id}' no encontrado en materiales.json. Disponibles: {list(all_config.keys())}")

    return all_config[gransic_key]


def initialize_sumadores4(config):
    """Inicializa sumadores dinamicos segun la config del GRANSIC."""
    tiene_peligrosidad = config["tiene_peligrosidad"]
    sumadores = {}

    for categoria, materiales in config["categorias"].items():
        if tiene_peligrosidad:
            sumadores[categoria] = {
                material: {"peligroso": 0.0, "no peligroso": 0.0}
                for material in materiales
            }
        else:
            sumadores[categoria] = {
                material: {"total": 0.0}
                for material in materiales
            }

    return sumadores


def generate_report4(matrix_data, sales_data, config):
    """Genera un reporte sumando toneladas de materiales por categoria, adaptado al GRANSIC."""

    sumadores = initialize_sumadores4(config)
    tiene_peligrosidad = config["tiene_peligrosidad"]
    categoria_keys = list(config["categorias"].keys())

    print(f"Procesando {len(sales_data)} registros de ventas...")
    print(f"Categorias: {categoria_keys}, Peligrosidad: {tiene_peligrosidad}")

    total_lines = len(sales_data)
    processed_correctly = 0
    not_found_entries = []

    for index, sale in enumerate(sales_data, start=1):
        producto_venta = str(sale.get('SKU', '')).strip()
        unidad_venta = str(sale.get('Unidad de venta', '')).strip().lower()
        cantidad_vendida = to_float2(sale.get('Cantidad', 0))

        if cantidad_vendida <= 0:
            print(f"Linea {index}: Cantidad <= 0, se omite. Producto: {producto_venta}, Unidad: {unidad_venta}")
            continue

        matching_items = [
            item for item in matrix_data
            if item.get('SKU', '').strip() == producto_venta and
               item.get('Unidad de venta', '').strip().lower() == unidad_venta
        ]

        if not matching_items:
            print(f"Linea {index}: No se encontro correspondencia para producto y unidad: {producto_venta} - {unidad_venta}")
            not_found_entries.append({
                "Linea del Registro de Ventas": index,
                "SKU": producto_venta,
                "Unidad de venta": unidad_venta
            })
            continue

        processed_correctly += 1

        for item in matching_items:
            material = item.get('Materiales', '').strip()
            categoria = item.get('Categoria', '') or item.get('Categoría', '')
            categoria = categoria.strip().lower()
            peso_por_unidad = to_float2(item.get('TON', 0))

            if not material or peso_por_unidad <= 0:
                print(f"Linea {index}: Material o peso invalido. Producto: {producto_venta}")
                continue

            peso_total = round(peso_por_unidad * cantidad_vendida, 8)
            print(f"Linea {index}: Material = {material}, Categoria = {categoria}, Peso Total = {peso_total}")

            # Buscar a cual categoria pertenece (orden largo->corto para evitar match parcial)
            matched_cat = None
            for cat_key in sorted(categoria_keys, key=len, reverse=True):
                if cat_key in categoria:
                    matched_cat = cat_key
                    break

            if matched_cat is None:
                print(f"Linea {index}: Categoria desconocida '{categoria}' para producto {producto_venta}")
                continue

            peligrosidad = item.get('Peligrosidad', '').strip().lower() if tiene_peligrosidad else None
            add_to_sumadores4(sumadores[matched_cat], material, peso_total, peligrosidad, tiene_peligrosidad)

    log_info = {
        "total_lines": total_lines,
        "processed_correctly": processed_correctly,
        "not_found_entries": not_found_entries
    }
    return format_report4(sumadores, tiene_peligrosidad), log_info


def add_to_sumadores4(sumadores, material, peso, peligrosidad, tiene_peligrosidad):
    if material in sumadores:
        if tiene_peligrosidad:
            key = "peligroso" if peligrosidad == "peligroso" else "no peligroso"
            sumadores[material][key] += peso
        else:
            sumadores[material]["total"] += peso
    else:
        print(f"ADVERTENCIA: Material '{material}' no encontrado en materiales.json. Peso {peso} TON no contabilizado.")


def format_report4(sumadores, tiene_peligrosidad):
    """Convierte sumadores en lista de diccionarios con columnas segun peligrosidad."""
    report = []
    for categoria, materiales in sumadores.items():
        for material, valores in materiales.items():
            if tiene_peligrosidad:
                peligroso = f"{valores.get('peligroso', 0.0):.8f}".replace('.', ',')
                no_peligroso = f"{valores.get('no peligroso', 0.0):.8f}".replace('.', ',')
                report.append({
                    "categoría": categoria,
                    "material": material,
                    "Materiales peligrosos": peligroso,
                    "Materiales no peligrosos": no_peligroso
                })
            else:
                total = f"{valores.get('total', 0.0):.8f}".replace('.', ',')
                report.append({
                    "categoría": categoria,
                    "material": material,
                    "Total": total
                })
    return report


# --- Funciones reutilizadas de v3 sin cambios ---

def get_file_data2(file_like_obj):
    """Lee y parsea un archivo Excel desde un objeto de tipo BytesIO."""
    df = pd.read_excel(file_like_obj, dtype=str)
    print(f"columnas del archivo: {df.columns.tolist()}")
    # Solo reemplazar comas por puntos en columnas numericas, no en texto
    columnas_numericas = ['TON', 'Cantidad', 'Peso', 'precio', 'Precio']
    for col in df.columns:
        if col in columnas_numericas:
            df[col] = df[col].map(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
    return df.to_dict(orient='records')


def save_report_to_memory2(report2):
    """Guarda el reporte en un objeto BytesIO y lo retorna."""
    df = pd.DataFrame(report2)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output


def to_float2(value):
    """Convierte valores a float de forma segura."""
    try:
        if value is None or str(value).strip() == '':
            print(f" Valor nulo o vacio detectado: {value}")
            return 0.0
        return round(float(str(value).replace(',', '.')), 8)
    except ValueError as e:
        print(f" Error al convertir a float: {value}, Error: {e}")
        return 0.0


def print_logs2(log_info):
    """Imprime los logs finales del procesamiento."""
    total_lines = log_info["total_lines"]
    processed_correctly = log_info["processed_correctly"]
    not_found_skus = log_info["not_found_entries"]

    print("\nResumen del procesamiento:")
    print(f"Total de lineas procesadas: {total_lines}")
    print(f"Lineas procesadas correctamente: {processed_correctly}")
    print(f"Lineas no procesadas (SKU no encontrado): {len(not_found_skus)}")
