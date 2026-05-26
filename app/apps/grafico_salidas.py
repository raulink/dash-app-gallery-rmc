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

# --- Configuración de Base de Datos ---
# --- Configuración de Base de Datos PostgreSQL ---
load_dotenv()
# Es buena práctica usar variables de entorno específicas para Postgres, pero puedes 
# mantener los nombres de variables anteriores en tu archivo .env si lo prefieres.
POSTGRES_USER = os.getenv('POSTGRES_USER') or 'postgres'
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD') or 'postgres'
POSTGRES_HOST = os.getenv('POSTGRES_HOST') or 'localhost'
POSTGRES_PORT = os.getenv('POSTGRES_PORT') or '5432' # Puerto por defecto 5432
POSTGRES_DB = os.getenv('POSTGRES_DB') or 'ingresos_db'

# Conéctate a la base de datos MySQL
connection_string = f'postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}'
engine = create_engine(connection_string) #create_engine('postgresql+psycopg2://mantto:Sistemas0,@192.168.100.50/Catalogo')

# Cargar datos desde la tabla 'salida' a un DataFrame
df = pd.read_sql('SELECT * FROM salidas;', engine)

# Convertir la columna 'fecha_salida' a tipo de datos datetime
df['fecha_salida'] = pd.to_datetime(df['fecha_salida'], dayfirst=True)

# Reemplazar `None` o `null` por un valor adecuado en las columnas problemáticas
df['grupo'] = df['grupo'].fillna('')
df['partida'] = df['partida'].fillna('')
df['ubicacion'] = df['ubicacion'].fillna('')

# --- Aplicación Dash ---
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    # Encabezado
    dbc.Row([
        dbc.Col(html.H2("Panel de Control de Salidas", className="text-center my-4"), width=12)
    ]),

    # Sección de Filtros Superiores
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Código de Item"),
                    dcc.Dropdown(
                        id='codigo-item-dropdown2',
                        options=[{'label': str(item), 'value': item} for item in df['codigo'].unique()],
                        placeholder='Selecciona código',
                        className="mb-3"
                    ),
                ], xs=12, md=4, lg=2),
                dbc.Col([
                    dbc.Label("Descripción"),
                    dcc.Dropdown(
                        id='item-dropdown2',
                        options=[{'label': str(desc), 'value': desc} for desc in df['item'].unique()],
                        placeholder='Selecciona descripción',
                        className="mb-9"
                    ),
                ], xs=12, md=4, lg=8),
                

                dbc.Col([
                    dbc.Label("Tipo de Gráfico"),
                    dcc.Dropdown(
                        id='tipo-grafico-dropdown2',
                        options=[
                            {'label': 'Barras Apiladas', 'value': 'bar_stack'},
                            {'label': 'Columnas Apiladas', 'value': 'bar_stack_col'},
                            {'label': 'Barras Agrupadas', 'value': 'bar_group'},
                            {'label': 'Columnas Agrupadas', 'value': 'bar_group_col'},
                            {'label': 'Líneas', 'value': 'line'},
                            {'label': 'Cintas (Funnel)', 'value': 'funnel'},
                            {'label': 'Circular', 'value': 'pie'},
                            {'label': 'Anillos', 'value': 'donut'},
                            {'label': 'Área', 'value': 'area'}
                        ],
                        placeholder='Tipo de gráfico',
                        value='area', # Valor por defecto
                        className="mb-3"
                    ),
                ], xs=12, md=4, lg=2),  
            ]),
        ])
    ], className="mb-4 shadow-sm"),

    # Sección de Información Detallada
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Detalles del Ítem Seleccionado"),
                dbc.CardBody([
                    dcc.Graph(
                        id='item-imagen2', 
                        config={'displayModeBar': False},
                        style={'height': '150px'}
                    ),
                ])
            ], className="mb-4 shadow-sm")
        ], width=12),
    ]),

    # Gráfico Principal
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='line-chart2'),
                ])
            ], className="mb-4 shadow-sm")
        ]),
    ]),

    # Footer con Resumen, Rango de Fechas y Exportación
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5("Resumen de Datos", className="card-title"),
                    dbc.Alert([
                        html.Div(id='suma-cantidad-label2'),
                        html.Div(id='precio-unitario-maximo-label2'),
                    ], color="success"), # Color verde para distinguir de ingresos
                ], xs=12, md=8),
                
                dbc.Col([
                    dbc.Label("Rango de Fechas de Salida"),
                    html.Br(),
                    dcc.DatePickerRange(
                        id='date-picker-range2',
                        min_date_allowed=df['fecha_salida'].min().date(),
                        max_date_allowed=df['fecha_salida'].max().date(),
                        start_date=df['fecha_salida'].min().date(),
                        end_date=df['fecha_salida'].max().date(),
                        display_format='YYYY-MM-DD',
                        style={'border': '1px solid #ccc', 'borderRadius': '4px', 'width': '100%'}
                    ),
                ], xs=12, md=4),

            ], align="center"),
        ])
    ], className="mb-5 shadow-sm"),

], fluid=True, style={'backgroundColor': '#f8f9fa'})

# --- Callbacks ---

@callback(
    [
        Output('line-chart2', 'figure'),
        Output('suma-cantidad-label2', 'children'),
        Output('precio-unitario-maximo-label2', 'children')
    ],
    [
        Input('codigo-item-dropdown2', 'value'),
        Input('item-dropdown2', 'value'),
        Input('date-picker-range2', 'start_date'),
        Input('date-picker-range2', 'end_date'),
        #Input('grupo-dropdown2', 'value'),
        #Input('partida-presupuestaria-dropdown2', 'value'),
        Input('tipo-grafico-dropdown2', 'value'),
        #Input('anio-dropdown2', 'value')
    ]
)
def update_graph_and_labels(codigo, item, start_date, end_date, tipo_grafico):
    df_filtrado = df.copy()

    # Aplicar filtros
    if codigo:
        df_filtrado = df_filtrado[df_filtrado['codigo'] == codigo]
    if item:
        df_filtrado = df_filtrado[df_filtrado['item'] == item]
    if start_date and end_date:
        df_filtrado = df_filtrado[(df_filtrado['fecha_salida'] >= start_date) & (df_filtrado['fecha_salida'] <= end_date)]
    #if anio:
    #    df_filtrado = df_filtrado[df_filtrado['fecha_salida'].dt.year == int(anio)]
    #if grupo:
    #    df_filtrado = df_filtrado[df_filtrado['grupo'] == grupo]
    #if partida:
    #    df_filtrado = df_filtrado[df_filtrado['partida'] == partida]

    # Agrupar datos por fecha (mes), ubicación, y sumar la cantidad
    df_agrupado = df_filtrado.groupby([df_filtrado['fecha_salida'].dt.to_period('M'), 'ubicacion'])['cantidad'].sum().reset_index()
    df_agrupado['fecha_salida'] = df_agrupado['fecha_salida'].astype(str)

    title_text = 'Cantidad por fecha de salida'
    
    # Crear gráfico según el tipo seleccionado
    if tipo_grafico == 'bar_stack':
        fig = px.bar(df_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=title_text, text='cantidad', labels={'cantidad': 'Cantidad'}, barmode='stack')
    elif tipo_grafico == 'bar_stack_col':
        fig = px.bar(df_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=title_text, text='cantidad', labels={'cantidad': 'Cantidad'}, barmode='stack')
    elif tipo_grafico == 'bar_group':
        fig = px.bar(df_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=title_text, text='cantidad', labels={'cantidad': 'Cantidad'}, barmode='group')
    elif tipo_grafico == 'bar_group_col':
        fig = px.bar(df_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=title_text, text='cantidad', labels={'cantidad': 'Cantidad'}, barmode='group')
    elif tipo_grafico == 'line':
        fig = px.line(df_agrupado, x='fecha_salida', y='cantidad', title=title_text, color='ubicacion', markers=True)
    elif tipo_grafico == 'funnel':
        fig = px.funnel(df_agrupado, x='fecha_salida', y='cantidad', title=title_text, color='ubicacion')
    elif tipo_grafico == 'pie':
        fig = px.pie(df_agrupado, names='ubicacion', values='cantidad', title='Cantidad por ubicación')
    elif tipo_grafico == 'donut':
        fig = px.pie(df_agrupado, names='ubicacion', values='cantidad', title='Cantidad por ubicación', hole=0.4)
    elif tipo_grafico == 'area':
        fig = px.area(df_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=title_text)
    else:
        fig = px.area(df_agrupado, x='fecha_salida', y='cantidad', color='ubicacion', title=title_text)

    fig.update_layout(template='plotly_white', margin=dict(t=50, b=20, l=20, r=20), height=500)

    # Calcular resúmenes
    suma_cantidad = df_filtrado['cantidad'].sum()
    punitario_maximo = df_filtrado['punitario'].max() if not df_filtrado.empty else 0
    
    suma_cantidad_label = f"Suma Total de Cantidades: {suma_cantidad}"
    punitario_maximo_label = f"Precio Unitario Máximo: ${punitario_maximo:,.2f}"

    return fig, suma_cantidad_label, punitario_maximo_label


@callback(
    Output('item-imagen2', 'figure'),
    [Input('codigo-item-dropdown2', 'value'),
     Input('item-dropdown2', 'value')]
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
                        f"<b>Partida:</b> {item.get('codigo_partida', 'N/A')} - {item.get('partida', 'N/A')}")
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
    app.run(debug=True, port=8051)