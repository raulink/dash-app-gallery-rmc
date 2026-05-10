import dash
from dash import dash_table, dcc, html
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
from sqlalchemy import create_engine # Para la conexión a Postgres

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Configuración de conexión a PostgreSQL
# Ajusta estos valores con tus credenciales reales
DB_URL = "postgresql://postgres:postgres@localhost:5432/ingresos_db"

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Sistema de Salidas</title>
        {%favicon%}
        {%css%}
        <style>
            body, div, table, td, th, button, input, .dash-spreadsheet {
                font-family: "Arial Narrow", Arial, sans-serif !important;
            }
            .modal-header .modal-title { font-weight: bold; }
        </style>
    </head>
    <body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>
'''

def obtener_datos():
    ruta_excel = 'uploads/Partidas_20240826.120509.xlsx'
    
    try:
        # Intento 1: Cargar desde Excel
        df_original = pd.read_excel(ruta_excel)
        print("Datos cargados exitosamente desde Excel.")
        
    except Exception as e:
        # Intento 2: Cargar desde Postgres si falla el Excel
        print(f"Excel no encontrado o error en lectura: {e}. Intentando desde PostgreSQL...")
        try:
            engine = create_engine(DB_URL)
            query = "SELECT * FROM partidas"
            df_original = pd.read_sql(query, engine)
            print("Datos cargados exitosamente desde PostgreSQL.")
        except Exception as db_e:
            print(f"Error crítico: No se pudo conectar a la base de datos: {db_e}")
            return pd.DataFrame() # Retorna DF vacío si ambos fallan

    # Procesamiento común de los datos
    if not df_original.empty:
        # Seleccionar columnas
        df = df_original[[
            'Nro.', 'Código', 'Clasificación', 'Descripción', 'Objeto Gasto', 'Observación'
        ]]
        
        # Filtrar por códigos específicos
        #codigos_interes = ['39800', '39700', '34120']
        #df = df[df['Código'].astype(str).isin(codigos_interes)]
        
        return df.astype(str)
    
    return df_original

def serve_layout():
    df = obtener_datos()
    
    if df.empty:
        return dbc.Container(html.H3("Error: No se encontraron datos en ninguna fuente."), className="p-5")

    cols = df.columns

    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H2("Visualizador de Partidas (Redundancia Excel/DB)", className="text-center my-4"), width=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                dash_table.DataTable(
                    id='table_partidas',
                    columns=[{"name": i, "id": i} for i in df.columns],
                    data=df.to_dict('records'),
                    
                    filter_action="native",
                    sort_action="native",
                    sort_mode="multi",
                    
                    style_cell_conditional=[
                        {'if': {'column_id': cols[0]}, 'width': '10px'},
                        {'if': {'column_id': cols[1]}, 'width': '20px'},
                        {'if': {'column_id': cols[2]}, 'width': '30px'},
                    ],
                    
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px',
                        'fontFamily': '"Arial Narrow", Arial, sans-serif',
                        'fontSize': '11px',
                        'minWidth': '100px',
                        'whiteSpace': 'normal',
                    },
                    
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'border': '1px solid black',
                        'fontFamily': '"Arial Narrow", Arial, sans-serif',
                        'fontSize': '11px',
                    },
                    
                    page_size=15,
                    fixed_rows={'headers': False},
                    style_table={'overflowX': 'auto', 'height': '600px'},
                )
            ], width=12)
        ])
    ], fluid=True)

app.layout = serve_layout()

if __name__ == '__main__':
    app.run(debug=True)