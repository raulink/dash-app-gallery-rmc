import os
import io
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from dash import Dash, dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go

load_dotenv()
# Es buena práctica usar variables de entorno específicas para Postgres, pero puedes 
# mantener los nombres de variables anteriores en tu archivo .env si lo prefieres.
POSTGRES_USER = os.getenv('POSTGRES_USER') or 'postgres'
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD') or 'postgres'
POSTGRES_HOST = os.getenv('POSTGRES_HOST') or 'localhost'
POSTGRES_PORT = os.getenv('POSTGRES_PORT') or '5432' # Puerto por defecto 5432
POSTGRES_DB = os.getenv('POSTGRES_DB') or 'ingresos_db'


# Crear el motor de conexión
connection_string = f'postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
engine = create_engine(connection_string)

# --- 2. Carga y Preparación de Datos ---
# Cargar Ingresos
df_ingresos = pd.read_sql('SELECT * FROM ingresos;', engine)
df_ingresos['fecha_ingreso'] = pd.to_datetime(df_ingresos['fecha_ingreso'], dayfirst=True)

# Cargar Salidas
df_salidas = pd.read_sql('SELECT * FROM salidas;', engine)
df_salidas['fecha_salida'] = pd.to_datetime(df_salidas['fecha_salida'], dayfirst=True)
df_salidas['grupo'] = df_salidas['grupo'].fillna('')
df_salidas['partida'] = df_salidas['partida'].fillna('')
df_salidas['ubicacion'] = df_salidas['ubicacion'].fillna('')

# --- 3. Opciones Unificadas para Filtros Globales ---
# Combinar valores únicos de ambas tablas para que el buscador sea global
codigos_unicos = list(set(df_ingresos['codigo'].dropna().unique()) | set(df_salidas['codigo'].dropna().unique()))
items_unicos = list(set(df_ingresos['item'].dropna().unique()) | set(df_salidas['item'].dropna().unique()))

codigo_options = [{'label': str(c), 'value': c} for c in codigos_unicos]
item_options = [{'label': str(i), 'value': i} for i in items_unicos]

# Encontrar la fecha mínima y máxima global entre ambas tablas
min_date_global = min(df_ingresos['fecha_ingreso'].min(), df_salidas['fecha_salida'].min()).date()
max_date_global = max(df_ingresos['fecha_ingreso'].max(), df_salidas['fecha_salida'].max()).date()

# --- 4. Aplicación Dash ---
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    # Encabezado
    dbc.Row([
        dbc.Col(html.H2("Panel Unificado de Ingresos y Salidas", className="text-center my-4 fw-bold"), width=12)
    ]),

    # Sección de Filtros Globales
    dbc.Card([
        dbc.CardHeader("Filtros Globales", className="bg-dark text-white fw-bold"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Código de Ítem"),
                    dcc.Dropdown(
                        id='filtro-codigo',
                        options=codigo_options,
                        value='3-02-00001', # <- SE AGREGÓ EL VALOR POR DEFECTO AQUÍ
                        placeholder='Selecciona código',
                        className="mb-3"
                    ),
                ], xs=12, md=3),
                dbc.Col([
                    dbc.Label("Descripción / Ítem"),
                    dcc.Dropdown(
                        id='filtro-item',
                        options=item_options,
                        placeholder='Selecciona descripción',
                        className="mb-3"
                    ),
                ], xs=12, md=4),
                dbc.Col([
                    dbc.Label("Rango de Fechas"),
                    html.Br(),
                    dcc.DatePickerRange(
                        id='filtro-fechas',
                        min_date_allowed=min_date_global,
                        max_date_allowed=max_date_global,
                        start_date=min_date_global,
                        end_date=max_date_global,
                        display_format='YYYY-MM-DD',
                        style={'width': '100%', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                    ),
                ], xs=12, md=3),
                dbc.Col([
                    dbc.Label("Tipo de Gráfico"),
                    dcc.Dropdown(
                        id='filtro-tipo-grafico',
                        options=[
                            {'label': 'Líneas', 'value': 'lineas'},
                            {'label': 'Barras Apiladas', 'value': 'bar_stack'},
                            {'label': 'Barras Agrupadas', 'value': 'bar_group'},
                            {'label': 'Área', 'value': 'area'},
                            {'label': 'Circular', 'value': 'pie'},
                            {'label': 'Treemap (Cintas)', 'value': 'funnel'},
                        ],
                        value='area', # Valor por defecto
                        className="mb-3"
                    ),
                ], xs=12, md=2),
            ]),
        ])
    ], className="mb-4 shadow-sm"),

    # Sección de Información Detallada del Ítem
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(
                        id='item-detalle-imagen', 
                        config={'displayModeBar': False},
                        style={'height': '100px'}
                    ),
                ], className="p-0")
            ], className="mb-4 shadow-sm")
        ], width=12),
    ]),

    # Sección Principal: Gráficos Lado a Lado
    dbc.Row([
        # ---------------- COLUMNA INGRESOS ----------------
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Gráfico de Ingresos", className="bg-primary text-white fw-bold"),
                dbc.CardBody([
                    dcc.Graph(id='grafico-ingresos', style={'height': '400px'}),
                    html.Hr(),
                    dbc.Alert([
                        html.Div(id='resumen-ingresos-suma', className="fw-bold"),
                        html.Div(id='resumen-ingresos-maximo'),
                    ], color="info", className="mb-3"),
                    
                ])
            ], className="mb-4 shadow-sm")
        ], xs=12, lg=6),

        # ---------------- COLUMNA SALIDAS ----------------
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Gráfico de Salidas", className="bg-success text-white fw-bold"),
                dbc.CardBody([
                    dcc.Graph(id='grafico-salidas', style={'height': '400px'}),
                    html.Hr(),
                    dbc.Alert([
                        html.Div(id='resumen-salidas-suma', className="fw-bold"),
                        html.Div(id='resumen-salidas-maximo'),
                    ], color="success", className="mb-3"),
                    
                ])
            ], className="mb-4 shadow-sm")
        ], xs=12, lg=6),
    ]),

], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'paddingTop': '20px'})


# --- 5. Lógica Unificada (Callbacks) ---
@callback(
    [
        Output('grafico-ingresos', 'figure'),
        Output('resumen-ingresos-suma', 'children'),
        Output('resumen-ingresos-maximo', 'children'),
        
        Output('grafico-salidas', 'figure'),
        Output('resumen-salidas-suma', 'children'),
        Output('resumen-salidas-maximo', 'children'),
        
        Output('item-detalle-imagen', 'figure')
    ],
    [
        Input('filtro-codigo', 'value'),
        Input('filtro-item', 'value'),
        Input('filtro-fechas', 'start_date'),
        Input('filtro-fechas', 'end_date'),
        Input('filtro-tipo-grafico', 'value')
    ]
)
def actualizar_dashboard_completo(codigo, item, start_date, end_date, tipo_grafico):
    
    # ------------------ PROCESAMIENTO INGRESOS ------------------
    df_ing = df_ingresos.copy()
    if codigo: df_ing = df_ing[df_ing['codigo'] == codigo]
    if item: df_ing = df_ing[df_ing['item'] == item]
    if start_date and end_date: df_ing = df_ing[(df_ing['fecha_ingreso'] >= start_date) & (df_ing['fecha_ingreso'] <= end_date)]

    suma_ing = df_ing['cantidad'].sum() if not df_ing.empty else 0
    max_ing = df_ing['punitario'].max() if not df_ing.empty else 0
    str_suma_ing = f"Total Ingresado: {suma_ing:,.2f}"
    str_max_ing = f"Precio Máximo (Ingreso): Bs{max_ing:,.2f}"

    titulo_ing = 'Ingresos por fecha'
    if tipo_grafico == 'bar_stack' or tipo_grafico == 'bar_stack_col':
        fig_ing = px.bar(df_ing, x='fecha_ingreso', y='cantidad', title=titulo_ing, color='item', barmode='stack')
    elif tipo_grafico == 'bar_group' or tipo_grafico == 'bar_group_col':
        fig_ing = px.bar(df_ing, x='fecha_ingreso', y='cantidad', title=titulo_ing, color='item', barmode='group')
    elif tipo_grafico == 'area':
        fig_ing = px.area(df_ing, x='fecha_ingreso', y='cantidad', title=titulo_ing, color='item')
    elif tipo_grafico == 'pie' or tipo_grafico == 'donut':
        fig_ing = px.pie(df_ing, names='item', values='cantidad', title='Distribución de Ingresos', hole=(0.4 if tipo_grafico=='donut' else 0))
    elif tipo_grafico == 'funnel':
        fig_ing = px.treemap(df_ing, path=['item'], values='cantidad', title='Jerarquía de Ingresos')
    else: # lineas por defecto
        fig_ing = px.line(df_ing, x='fecha_ingreso', y='cantidad', title=titulo_ing, markers=True, color='item')
    
    fig_ing.update_layout(template='plotly_white', margin=dict(t=40, b=20, l=20, r=20))

    # ------------------ PROCESAMIENTO SALIDAS ------------------
    df_sal = df_salidas.copy()
    if codigo: df_sal = df_sal[df_sal['codigo'] == codigo]
    if item: df_sal = df_sal[df_sal['item'] == item]
    if start_date and end_date: df_sal = df_sal[(df_sal['fecha_salida'] >= start_date) & (df_sal['fecha_salida'] <= end_date)]

    # Agrupar Salidas por Mes y Ubicación (Lógica de tu archivo original)
    if not df_sal.empty:
        df_sal_agrupado = df_sal.groupby([df_sal['fecha_salida'].dt.to_period('M'), 'ubicacion'])['cantidad'].sum().reset_index()
        df_sal_agrupado['fecha_salida'] = df_sal_agrupado['fecha_salida'].astype(str)
    else:
        df_sal_agrupado = pd.DataFrame(columns=['fecha_salida', 'ubicacion', 'cantidad'])

    suma_sal = df_sal['cantidad'].sum() if not df_sal.empty else 0
    max_sal = df_sal['punitario'].max() if not df_sal.empty else 0
    str_suma_sal = f"Total Salidas: {suma_sal:,.2f}"
    str_max_sal = f"Precio Unitario Máximo (Salida): Bs{max_sal:,.2f}"

    titulo_sal = 'Salidas por fecha (Agrupado por mes)'
    if tipo_grafico == 'bar_stack' or tipo_grafico == 'bar_stack_col':
        fig_sal = px.bar(df_sal_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=titulo_sal, text='cantidad', barmode='stack')
    elif tipo_grafico == 'bar_group' or tipo_grafico == 'bar_group_col':
        fig_sal = px.bar(df_sal_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=titulo_sal, text='cantidad', barmode='group')
    elif tipo_grafico == 'area':
        fig_sal = px.area(df_sal_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=titulo_sal)
    elif tipo_grafico == 'pie' or tipo_grafico == 'donut':
        fig_sal = px.pie(df_sal_agrupado, names='ubicacion', values='cantidad', title='Distribución por Ubicación', hole=(0.4 if tipo_grafico=='donut' else 0))
    elif tipo_grafico == 'funnel':
        fig_sal = px.funnel(df_sal_agrupado, x='fecha_salida', y='cantidad', title=titulo_sal, color='ubicacion')
    else: # lineas por defecto
        fig_sal = px.line(df_sal_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=titulo_sal, markers=True)
    
    fig_sal.update_layout(template='plotly_white', margin=dict(t=40, b=20, l=20, r=20))

    # ------------------ DETALLE EN TEXTO (IMAGEN) ------------------
    # Busca la información primero en ingresos, si no hay, la busca en salidas
    item_info = None
    if not df_ing.empty:
        item_info = df_ing.iloc[0]
    elif not df_sal.empty:
        item_info = df_sal.iloc[0]

    if item_info is not None:
        c_val = item_info['codigo']
        i_val = item_info['item']
        # Usa .get() para evitar errores si las columnas de partida se llaman diferente en cada tabla
        p_val = item_info.get('partida', item_info.get('partida_presupuestaria', 'N/A'))
        text_content = f"<b>Código:</b> {c_val} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Descripción:</b> {i_val} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Partida:</b> {p_val}"
    else:
        text_content = "Seleccione un ítem con datos válidos para ver los detalles"

    fig_detalle = go.Figure()
    fig_detalle.add_annotation(
        text=text_content, xref="paper", yref="paper", font=dict(size=18),
        showarrow=False, x=0.5, y=0.5, xanchor='center', yanchor='middle'
    )
    fig_detalle.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig_ing, str_suma_ing, str_max_ing, fig_sal, str_suma_sal, str_max_sal, fig_detalle

if __name__ == '__main__':
    app.run(debug=True, port=8050)