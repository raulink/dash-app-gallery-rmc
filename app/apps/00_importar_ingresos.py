import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from sqlalchemy import create_engine, Table, Column, String, Integer, MetaData, inspect

# --- CONFIGURACIÓN DE POSTGRES ---
DB_USER = "postgres"
DB_PASS = "postgres"
DB_HOST = "db"  # Nombre del servicio en docker-compose
DB_PORT = "5432"
DB_NAME = "ingresos_db"

tabla = "ingresos"  # Nombre de la tabla en PostgreSQL

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL, 
    connect_args={'client_encoding': 'utf8'}
)
metadata = MetaData()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- APLICACIÓN DASH ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Sistema de Ingresos</title>
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

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("CONTROL DE INGRESOS - MI TELEFÉRICO", 
                        className="text-center text-primary my-4", 
                        style={'fontWeight': 'bold'}), width=12)
    ]),

    # Panel de Carga
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-data-i',
                        children=dbc.Button("📂 SELECCIONAR ARCHIVO EXCEL", color="primary", outline=True),
                        multiple=False
                    ),
                    html.Div(id='status-msg-i', className="mt-2 text-muted", style={'fontSize': '12px'})
                ], className="text-center")
            ], className="shadow-sm mb-4")
        ], width=8, className="mx-auto")
    ]),

    # Modal de Selección
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("SELECCIÓN DE REGISTROS PARA IMPORTAR")),
        dbc.ModalBody([
            dbc.ButtonGroup([
                dbc.Button("SELECCIONAR TODOS", id="select-all-i", color="dark", outline=True, size="sm"),
                dbc.Button("LIMPIAR", id="deselect-all-i", color="danger", outline=True, size="sm"),
            ], className="mb-3"),
            dash_table.DataTable(
                id='modal-table-i',
                row_selectable='multi',
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                filter_action="native"
            ),
        ]),
        dbc.ModalFooter(
            dbc.Button("GUARDAR EN POSTGRESQL", id="btn-db-save-i", color="success")
        ),
    ], id="modal-selection-i", size="xl", is_open=False, backdrop="static"),

    # Visualización Principal
    dbc.Row([
        dbc.Col([
            html.H5("DATOS ALMACENADOS EN EL SISTEMA", className="text-secondary"),
            dash_table.DataTable(
                id='main-table-i',
                filter_action="native",
                sort_action="native",
                page_action="native",
                page_size=15,
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'padding': '10px', 'textAlign': 'left'}
            ),
        ], width=12)
    ])
], fluid=True)

# --- FUNCIONES ---

def limpiar_unicode(df):
    df = df.replace({'\u2010': '-', '\u2013': '-', '\u2014': '-'}, regex=True)
    return df.astype(str)

def cargar_datos_inicio():
    try:
        query = f"SELECT * FROM {tabla} ORDER BY id ASC"
        df = pd.read_sql(query, con=engine)
        cols = [{"name": i, "id": i} for i in df.columns]
        return df.to_dict('records'), cols
    except Exception as e:
        print(f"Error al cargar inicio: {e}")
        return [], []
    
def ensure_table_exists(columns):
    inspector = inspect(engine)
    if not inspector.has_table(tabla):
        cols = [Column('id_auto', Integer, primary_key=True, autoincrement=True)]
        for col in columns:
            cols.append(Column(col.strip(), String))
        new_table = Table(tabla, metadata, *cols)
        metadata.create_all(engine)

def save_to_server(filename, contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(decoded)
    return path

# --- CALLBACKS ---

# 1. Carga inicial
@app.callback(
    [Output('main-table-i', 'data'),
     Output('main-table-i', 'columns')],
    [Input('main-table-i', 'id')] 
)
def inicializar_tabla(instance_id):
    return cargar_datos_inicio()

# 2. Procesar Upload
@app.callback(
    [Output('modal-selection-i', 'is_open'),
     Output('modal-table-i', 'data'),
     Output('modal-table-i', 'columns'),
     Output('status-msg-i', 'children')],
    [Input('upload-data-i', 'contents')],
    [State('upload-data-i', 'filename')],
    prevent_initial_call=True
)
def process_upload(contents, filename):
    if contents:
        try:
            path = save_to_server(filename, contents)
            df = pd.read_excel(path, skiprows=7, engine='openpyxl')
            
            # Limpieza según tu lógica
            if 'Código Ingreso' in df.columns:
                df = df[df['Código Ingreso'].notna()]

            columnas_ui_nombres = ['Nº', 'Sistema', 'Tipo Ingreso', 'Fecha Ingreso', 'Código Ingreso', 'Estado', 'Motivo de Ingreso', 'Gerencia Solicitante', 'Departamento Solicitante', 'Ubicación', 'Tipo de Gasto', 'Partida Presupuestaria','Proveedor', 'Código Item', 'Código Anterior Item', 'Item', 'Unidad Medida', 'Grupo', 'Subgrupo', 'Cantidad', 'Precio Unitario 100%', 'Importe (Histórico) 100%', 'CF-IVA', 'Importe Calculado']
            columnas_db = ['id', 'sistema', 'tipo', 'fecha_ingreso', 'codigo_ingreso', 'estado', 'motivo', 'gerencia', 'departamento', 'ubicacion', 'gasto', 'partida', 'proveedor', 'codigo', 'codigo_anterior', 'item', 'unidad', 'grupo', 'subgrupo', 'cantidad', 'punitario', 'total', 'impuesto', 'calculado']

            mapping = dict(zip(columnas_ui_nombres, columnas_db))
            df = df.rename(columns=mapping)
            
            # Solo enviamos a la BD las columnas mapeadas que existen en el DF
            cols_to_keep = [c for c in columnas_db if c in df.columns]
            df = df[cols_to_keep]
            
            df = limpiar_unicode(df)
            
            # El id del excel se ignora para que Postgres use el autoincremental (id_auto)
            if 'id' in df.columns:
                df = df.drop(columns=['id'])

            # Asegurar tabla (usando las columnas de la BD menos el id_auto)
            cols_for_sql = [c for c in df.columns]
            ensure_table_exists(cols_for_sql)

            cols_ui_formatted = [{"name": i, "id": i} for i in df.columns]
            return True, df.to_dict('records'), cols_ui_formatted, f"Archivo procesado: {filename}"
        
        except Exception as e:
            print(f"DEBUG ERROR: {str(e)}")
            return False, [], [], f"Error: {str(e)}"
    return dash.no_update

# 3. Selección masiva
@app.callback(
    Output('modal-table-i', 'selected_rows'),
    [Input('select-all-i', 'n_clicks'),
     Input('deselect-all-i', 'n_clicks')],
    State('modal-table-i', 'data'),
    prevent_initial_call=True
)
def handle_selection(s, d, data):
    ctx = callback_context
    if ctx.triggered_id == 'select-all-i':
        return list(range(len(data)))
    return []

# 4. Guardar y Refrescar (CON allow_duplicate=True)
@app.callback(
    [Output('modal-selection-i', 'is_open', allow_duplicate=True),
     Output('main-table-i', 'data', allow_duplicate=True),
     Output('main-table-i', 'columns', allow_duplicate=True)],
    [Input('btn-db-save-i', 'n_clicks')],
    [State('modal-table-i', 'data'),
     State('modal-table-i', 'selected_rows')],
    prevent_initial_call=True
)
def save_db(n, table_data, selected_indices):
    if n and selected_indices:
        selected_df = pd.DataFrame([table_data[i] for i in selected_indices])
        
        # Insertar en SQL
        selected_df.to_sql(tabla, con=engine, if_exists='append', index=False)
        
        # Obtener datos frescos ordenados para la tabla principal
        data, cols = cargar_datos_inicio()
        return False, data, cols
    
    return dash.no_update, dash.no_update, dash.no_update

if __name__ == '__main__':
    app.run(debug=False)