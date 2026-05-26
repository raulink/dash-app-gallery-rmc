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

# --- Configuración de Base de Datos PostgreSQL ---
load_dotenv()
# Es buena práctica usar variables de entorno específicas para Postgres, pero puedes 
# mantener los nombres de variables anteriores en tu archivo .env si lo prefieres.
POSTGRES_USER = os.getenv('POSTGRES_USER') or 'postgres'
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD') or 'postgres'
POSTGRES_HOST = os.getenv('POSTGRES_HOST') or 'localhost'
POSTGRES_PORT = os.getenv('POSTGRES_PORT') or '5432' # Puerto por defecto 5432
POSTGRES_DB = os.getenv('POSTGRES_DB') or 'ingresos_db'

# Crear la URL de conexión para PostgreSQL usando psycopg2
connection_string = f'postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}'
engine = create_engine(connection_string)

# Cargar datos
df = pd.read_sql('SELECT * FROM ingresos;', engine)
df['fecha_ingreso'] = pd.to_datetime(df['fecha_ingreso'], dayfirst=True)

# Opciones para Dropdowns
codigo_options = [{'label': item, 'value': item} for item in df['codigo'].unique()]
item_options = [{'label': desc, 'value': desc} for desc in df['item'].unique()]
#anio_options = [{'label': str(anio), 'value': anio} for anio in df['fecha_ingreso'].dt.year.unique()]

# --- Aplicación Dash ---
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    # Encabezado
    dbc.Row([
        dbc.Col(html.H2("Panel de Control de Ingresos", className="text-center my-4"), width=12)
    ]),

    # Sección de Filtros Superiores
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Código de Ítem"),
                    dcc.Dropdown(
                        id='codigo-item-dropdown1',
                        options=codigo_options,
                        placeholder='Selecciona código',
                        className="mb-3"
                    ),
                ], xs=12, md=3),
                dbc.Col([
                    dbc.Label("Descripción"),
                    dcc.Dropdown(
                        id='item-dropdown1',
                        options=item_options,
                        placeholder='Selecciona descripción',
                        className="mb-3"
                    ),
                ], xs=12, md=6),
                
                # TODO: Eliminar año
                #dbc.Col([
                #    dbc.Label("Año"),
                #    dcc.Dropdown(
                #        id='anio-dropdown1',
                #        options=anio_options,
                #        placeholder='Selecciona año',
                #        className="mb-3"
                #    ),
                #], xs=12, md=3),
                dbc.Col([
                    dbc.Label("Tipo de Gráfico"),
                    dcc.Dropdown(
                        id='tipo-grafico-dropdown1',
                        options=[
                            {'label': 'Barras Apiladas', 'value': 'barras_apiladas'},
                            {'label': 'Columnas Apiladas', 'value': 'columnas_apiladas'},
                            {'label': 'Barras Agrupadas', 'value': 'barras_agrupadas'},
                            {'label': 'Columnas Agrupadas', 'value': 'columnas_agrupadas'},
                            {'label': 'Líneas', 'value': 'lineas'},
                            {'label': 'Treemap (Cintas)', 'value': 'cintas'},
                            {'label': 'Circular', 'value': 'circular'},
                            {'label': 'Anillos', 'value': 'anillos'},
                            {'label': 'Área', 'value': 'area'}
                        ],
                        placeholder='Tipo de gráfico',
                        value='lineas',
                        className="mb-3"
                    ),
                ], xs=12, md=3),
            ]),
        ])
    ], className="mb-4 shadow-sm"),

        # Gráfico Principal
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='line-chart1'),
                ])
            ], className="mb-4 shadow-sm")
        ], width=12)
    ]),
    # Sección de Información Detallada (La "Imagen")
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Detalles del Ítem Seleccionado"),
                dbc.CardBody([
                    dcc.Graph(
                        id='item-imagen1', 
                        config={'displayModeBar': False},
                        style={'height': '150px'}
                    ),
                ])
            ], className="mb-4 shadow-sm")
        ], width=12),
    ]),
    # Footer con Resumen y Exportación
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5("Resumen de Datos", className="card-title"),
                    dbc.Alert([
                        html.Div(id='suma-cantidad-label1'),
                        html.Div(id='precio-unitario-maximo-label1'),
                    ], color="info"),
                ], xs=12, md=8),
                
                dbc.Col([
                    dbc.Label("Rango de Fechas"),
                    html.Br(),
                    dcc.DatePickerRange(
                        id='date-picker-range1',
                        min_date_allowed=df['fecha_ingreso'].min().date(),
                        max_date_allowed=df['fecha_ingreso'].max().date(),
                        start_date=df['fecha_ingreso'].min().date(),
                        end_date=df['fecha_ingreso'].max().date(),
                        display_format='YYYY-MM-DD',
                        style={'border': '1px solid #ccc', 'borderRadius': '4px'}
                    ),
                ], xs=12, md=4),

                
            ], align="center"),
        ])
    ], className="mb-5 shadow-sm"),

], fluid=True, style={'backgroundColor': '#f8f9fa'})

# --- Callbacks ---

@callback(
    [
        Output('line-chart1', 'figure'),
        Output('suma-cantidad-label1', 'children'),
        Output('precio-unitario-maximo-label1', 'children')
    ],
    [
        Input('codigo-item-dropdown1', 'value'),
        Input('item-dropdown1', 'value'),
        Input('date-picker-range1', 'start_date'),
        Input('date-picker-range1', 'end_date'),
        Input('tipo-grafico-dropdown1', 'value')
        #Input('anio-dropdown1', 'value'),
    ]
)
def update_graph(codigo, item, start_date, end_date, tipo_grafico):
    df_filtrado = df.copy()

    if codigo:
        df_filtrado = df_filtrado[df_filtrado['codigo'] == codigo]
    if item:
        df_filtrado = df_filtrado[df_filtrado['item'] == item]
    if start_date and end_date:
        df_filtrado = df_filtrado[(df_filtrado['fecha_ingreso'] >= start_date) & (df_filtrado['fecha_ingreso'] <= end_date)]
    #if anio:
    #    df_filtrado = df_filtrado[df_filtrado['fecha_ingreso'].dt.year == int(anio)]

    # Lógica de creación de gráficos
    title_text = 'Cantidad por fecha de ingreso'
    
    if tipo_grafico == 'barras_apiladas':
        fig = px.bar(df_filtrado, x='fecha_ingreso', y='cantidad', title=title_text, color='item', barmode='stack')
    elif tipo_grafico == 'columnas_apiladas':
        fig = px.bar(df_filtrado, x='fecha_ingreso', y='cantidad', title=title_text, color='item', barmode='stack')
    elif tipo_grafico == 'barras_agrupadas':
        fig = px.bar(df_filtrado, x='fecha_ingreso', y='cantidad', title=title_text, color='item', barmode='group')
    elif tipo_grafico == 'columnas_agrupadas':
        fig = px.bar(df_filtrado, x='fecha_ingreso', y='cantidad', title=title_text, color='item', barmode='group')
    elif tipo_grafico == 'lineas':
        fig = px.line(df_filtrado, x='fecha_ingreso', y='cantidad', title=title_text, markers=True)
    elif tipo_grafico == 'cintas':
        fig = px.treemap(df_filtrado, path=['item'], values='cantidad', title='Cantidad por descripción')
    elif tipo_grafico == 'circular':
        fig = px.pie(df_filtrado, names='item', values='cantidad', title='Distribución de cantidades')
    elif tipo_grafico == 'anillos':
        fig = px.pie(df_filtrado, names='item', values='cantidad', title='Distribución de cantidades', hole=0.3)
    elif tipo_grafico == 'area':
        fig = px.area(df_filtrado, x='fecha_ingreso', y='cantidad', title=title_text)
    else:
        fig = px.line(df_filtrado, x='fecha_ingreso', y='cantidad', title=title_text, markers=True)
    
    fig.update_layout(template='plotly_white', margin=dict(t=50, b=20, l=20, r=20))
    
    suma_cantidad = df_filtrado['cantidad'].sum()
    punitario_maximo = df_filtrado['punitario'].max() if not df_filtrado.empty else 0
    
    return fig, f"Suma Total: {suma_cantidad}", f"Precio Máximo: Bs{punitario_maximo:,.2f}"

@callback(
    Output('item-imagen1', 'figure'),
    [Input('codigo-item-dropdown1', 'value'),
     Input('item-dropdown1', 'value')]
)
def generate_image(codigo, item):
    df_filtrado = df.copy()
    if codigo:
        df_filtrado = df_filtrado[df_filtrado['codigo'] == codigo]
    elif item:
        df_filtrado = df_filtrado[df_filtrado['item'] == item]

    if not df_filtrado.empty:
        item = df_filtrado.iloc[0]
        text_content = (f"<b>Código:</b> {item['codigo']} | <b>Descripción:</b> {item['item']}<br>"
                        f"<b>Partida:</b> {item.get('codigo_partida', 'N/A')} - {item.get('partida_presupuestaria', 'N/A')}")
    else:
        text_content = "Seleccione un ítem para ver los detalles"

    fig = go.Figure()
    fig.add_annotation(
        text=text_content,
        xref="paper", yref="paper",
        font=dict(size=16),
        showarrow=False, x=0.5, y=0.5
    )
    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


if __name__ == '__main__':
    app.run(debug=True, port=8050)