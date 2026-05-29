from sshtunnel import SSHTunnelForwarder
import psycopg2
import pandas as pd
import warnings

# Suprimir advertencia de Pandas sobre el uso directo de conexiones DBAPI
warnings.filterwarnings('ignore', category=UserWarning)

class DatabaseConnector:
    def __init__(self, ssh_params, db_params):
        """
        Inicializa la clase con los parámetros de conexión.
        
        :param ssh_params: Diccionario con credenciales y datos del host SSH.
        :param db_params: Diccionario con credenciales y datos de la base de datos.
        """
        self.ssh_host = ssh_params.get('host')
        self.ssh_port = ssh_params.get('port', 22)
        self.ssh_user = ssh_params.get('user')
        self.ssh_password = ssh_params.get('password')
        
        self.db_host = db_params.get('host')
        self.db_port = db_params.get('port', 5432)
        self.db_name = db_params.get('name')
        self.db_user = db_params.get('user')
        self.db_password = db_params.get('password')

    def get_dataframe(self, query):
        """
        Abre el túnel SSH, se conecta a la base de datos, ejecuta la consulta
        y retorna los resultados en un DataFrame de Pandas.
        
        :param query: Cadena de texto con la consulta SQL.
        :return: DataFrame de Pandas con los datos o None si ocurre un error.
        """
        try:
            # Establecer el túnel SSH
            with SSHTunnelForwarder(
                (self.ssh_host, self.ssh_port),
                ssh_username=self.ssh_user,
                ssh_password=self.ssh_password,
                remote_bind_address=(self.db_host, self.db_port),
                local_bind_address=('127.0.0.1', 0)  # El puerto 0 asigna uno libre automáticamente
            ) as tunnel:

                # Conectar a la base de datos PostgreSQL
                conn = psycopg2.connect(
                    dbname=self.db_name,
                    user=self.db_user,
                    password=self.db_password,
                    host='127.0.0.1',
                    port=tunnel.local_bind_port
                )
                
                # Leer los datos usando Pandas
                df = pd.read_sql_query(query, conn)
                
                # Cerrar la conexión interna a la BD
                conn.close()
                
                return df
                
        except Exception as e:
            print(f"❌ Error de conexión o consulta: {e}")
            return None
        
        
# 1. Definir los parámetros usando diccionarios
ssh_config = {
    'host': '192.168.100.50',
    'port': 22,
    'user': 'mantenimiento',
    'password': 'm1t3l3f3r1c02019.' # Usa variables de entorno (.env) en producción
}

db_config = {
    'host': '192.168.100.56',
    'port': 5432,
    'name': 'db_mantenimiento',
    'user': 'user_gom_mantenimiento',
    'password': 'M4ntenim13nto.' # Usa variables de entorno (.env) en producción
}

# 2. Tu consulta SQL
mi_query = """
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
FROM work_orders
INNER JOIN unplanned ON work_orders."id" = unplanned.fk_work_order
INNER JOIN classifiers AS categoria ON work_orders.fkc_work_order_type = categoria."id"
INNER JOIN assets ON unplanned.fk_asset = assets."id"
INNER JOIN base ON assets.fk_base = base."id"
INNER JOIN "structure" ON base.fk_structure = "structure"."id"
INNER JOIN locations ON base.fk_location = locations."id"
INNER JOIN locations AS linea ON work_orders.fk_line = linea."id"
INNER JOIN subsystems ON "structure".fk_subsystem = subsystems."id"
INNER JOIN systems ON subsystems.fk_system = systems."id"
ORDER BY unplanned.id;
"""

# 3. Instanciar la clase y obtener el DataFrame
conector = DatabaseConnector(ssh_params=ssh_config, db_params=db_config)
df_resultado = conector.get_dataframe(mi_query)

# 4. Validar y usar el DataFrame
if df_resultado is not None:
    print(f"✅ Consulta exitosa. Filas: {len(df_resultado)}")
    print(df_resultado.head())
else:
    print("⚠️ No se pudo obtener el DataFrame.")