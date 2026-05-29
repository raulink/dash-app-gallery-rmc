# %%
import pandas as pd
from sqlalchemy import create_engine

# --- 1. CONFIGURACIÓN DE LA BASE DE DATOS ---
DB_USER = "postgres"
DB_PASS = "postgres"
DB_HOST = "192.168.100.50"
DB_PORT = "5433"
DB_NAME = "ingresos_db"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# --- 2. EXTRACCIÓN DE DATOS ---
# Nota: El doble signo de porcentaje (%%) se usa a veces en Python para escapar el '%' 
# en consultas SQL dentro de ciertos drivers, pero pandas suele aceptar el '%' simple.
query = """
    SELECT * FROM salidas 
    WHERE codigo LIKE '6-06-%' 
    AND gerencia = 'GERENCIA DE OPERACION Y MANTENIMIENTO'
"""

print("Extrayendo datos de la base de datos...")

# Leemos directamente a un DataFrame
df = pd.read_sql(query, con=engine)


# Nos aseguramos de que la columna cantidad sea numérica para poder sumarla
df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)

# --- 3. ANÁLISIS DE ROTACIÓN ---
print("\nProcesando análisis de rotación (frecuencia y volumen)...")

# Agrupamos por código e ítem para contar las salidas y sumar las cantidades
analisis_rotacion = df.groupby(['codigo', 'item']).agg(
    frecuencia_salidas=('codigo', 'count'),      # Veces que se solicitó
    cantidad_total=('cantidad', 'sum')           # Total de unidades consumidas
).reset_index()

# Ordenamos de mayor a menor frecuencia para ver los más solicitados primero
analisis_rotacion = analisis_rotacion.sort_values(by='frecuencia_salidas', ascending=False)

# --- 4. RESULTADOS ---
print("\n" + "="*70)
print(" TOP INSUMOS QUÍMICOS DE MAYOR ROTACIÓN (Por Frecuencia de Salida)")
print("="*70)

# Mostramos los 15 insumos con mayor movimiento
top_15 = analisis_rotacion.head(15)

# Formateamos la salida en la consola
for index, row in top_15.iterrows():
    print(f"Código: {row['codigo']}")
    print(f"Ítem:   {row['item']}")
    print(f"        -> Frecuencia de retiros: {row['frecuencia_salidas']} veces")
    print(f"        -> Volumen total retirado: {row['cantidad_total']} unidades")
    print("-" * 50)
    
# Opcional: Exportar el resultado a un archivo Excel para revisión formal
analisis_rotacion.to_excel("rotacion_quimicos_mantenimiento.xlsx", index=False)
print("\nReporte exportado exitosamente a 'rotacion_quimicos_mantenimiento.xlsx'")




