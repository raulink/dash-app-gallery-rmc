from sshtunnel import SSHTunnelForwarder
import psycopg2
import pandas as pd
import warnings

# Suprimir advertencia de Pandas sobre el uso directo de conexiones DBAPI (opcional pero recomendado)
warnings.filterwarnings('ignore', category=UserWarning)

# Parámetros SSH
SSH_HOST = '192.168.100.50'
SSH_PORT = 22
SSH_USER = 'mantenimiento'  # ← Cambia esto
SSH_PASSWORD = 'm1t3l3f3r1c02019.'  # ← Cambia esto

# Parámetros de la base de datos
DB_HOST = '192.168.100.56'
DB_PORT = 5432
DB_NAME = 'db_mantenimiento'
DB_USER = 'user_gom_mantenimiento'
DB_PASSWORD = 'M4ntenim13nto.'

# SQL query
query = """
SELECT 
    unplanned.*, 
    linea."location" AS linea, 
    "structure"."name", 
    "structure".tag, 
    locations."location", 
    locations.location_code, 
    categoria."name" AS "Categoria", 
    systems."name" AS sistema, 
    subsystems."name" AS subsistema
FROM
    work_orders
    INNER JOIN unplanned 
        ON work_orders."id" = unplanned.fk_work_order
    INNER JOIN classifiers AS categoria 
        ON work_orders.fkc_work_order_type = categoria."id"
    INNER JOIN assets 
        ON unplanned.fk_asset = assets."id"
    INNER JOIN base 
        ON assets.fk_base = base."id"
    INNER JOIN "structure" 
        ON base.fk_structure = "structure"."id"
    INNER JOIN locations 
        ON base.fk_location = locations."id"
    INNER JOIN locations AS linea 
        ON work_orders.fk_line = linea."id"
    INNER JOIN subsystems 
        ON "structure".fk_subsystem = subsystems."id"
    INNER JOIN systems 
        ON subsystems.fk_system = systems."id"
ORDER BY unplanned.id;
"""

# Establecer el túnel SSH
with SSHTunnelForwarder(
    (SSH_HOST, SSH_PORT),
    ssh_username=SSH_USER,
    ssh_password=SSH_PASSWORD,
    remote_bind_address=(DB_HOST, DB_PORT),
    local_bind_address=('127.0.0.1', 6543)  # puerto local arbitrario
) as tunnel:

    # Conectar a la base de datos PostgreSQL a través del túnel SSH
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host='127.0.0.1',
            port=tunnel.local_bind_port
        )
        
        # Leer los datos usando Pandas
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Mostrar el resultado
        print(f"Consulta ejecutada con éxito. Filas recuperadas: {len(df)}")
        df.head()
        
    except Exception as e:
        print(f"Error de conexión o consulta: {e}")