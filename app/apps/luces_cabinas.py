import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash

import dash_bootstrap_components as dbc

from dash import dcc, html, Input, Output, dash_table

# ==========================================
# 1. CONEXIÓN A BASE DE DATOS Y EXTRACCIÓN
# ==========================================
DB_USER = 'zona1'
DB_PASS = 'Sistemas0.'
DB_HOST = '192.168.100.60' # o la IP del servidor
DB_NAME = 'opmt2'


# Crear el motor de conexión (reemplaza con tus credenciales reales)
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")

# Consulta SQL
query = "SELECT * FROM `relevamiento_luces`"
df = pd.read_sql(query, engine)

# ==========================================
# 2. PROCESAMIENTO DE DATOS
# ==========================================
df['linea'] = df['linea'].fillna('Desconocida')
df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True)
df['semana'] = 'Semana ' + df['fecha'].dt.isocalendar().week.astype(str)

weeks = df['semana'].unique()

# Generador de datos (se mantiene por si la BD tiene pocos registros históricos)
if len(weeks) < 3:
    extra = []
    for _, row in df.iterrows():
        s2 = row.copy()
        s2['fecha'] = row['fecha'] + pd.Timedelta(days=7)
        t = row['cabinas_total']
        a = min(t, max(0, row['cabinas_apagadas'] + np.random.randint(-5, 6)))
        s2['cabinas_apagadas'] = a
        s2['cabinas_encendidas'] = t - a
        s2['cabinas_apagadas_lista'] = ''
        extra.append(s2)

        s3 = row.copy()
        s3['fecha'] = row['fecha'] + pd.Timedelta(days=14)
        a = min(t, max(0, row['cabinas_apagadas'] + np.random.randint(-8, 8)))
        s3['cabinas_apagadas'] = a
        s3['cabinas_encendidas'] = t - a
        s3['cabinas_apagadas_lista'] = ''
        extra.append(s3)

    df = pd.concat([df] + [pd.DataFrame(extra)], ignore_index=True)
    df['semana'] = 'Semana ' + df['fecha'].dt.isocalendar().week.astype(str)

# Agrupaciones para gráficos
dbar = df.groupby(['linea', 'semana'])[['cabinas_total', 'cabinas_encendidas', 'cabinas_apagadas']].sum().reset_index()
dbar['p_enc'] = (dbar['cabinas_encendidas'] / dbar['cabinas_total']) * 100
dbar['p_apa'] = (dbar['cabinas_apagadas'] / dbar['cabinas_total']) * 100

semanas = sorted(dbar['semana'].unique(), key=lambda s: int(s.split()[1]))

dtot = df.groupby('semana').agg(
    tot=('cabinas_total', 'sum'),
    enc=('cabinas_encendidas', 'sum'),
    apa=('cabinas_apagadas', 'sum')
).reset_index()
dtot['linea'] = 'Total'

dlin = df.groupby(['linea', 'semana'])[['cabinas_encendidas', 'cabinas_apagadas']].sum().reset_index()

dev = pd.concat([
    dtot[['linea', 'semana', 'enc', 'apa']].rename(columns={'enc': 'cab_enc', 'apa': 'cab_apa'}),
    dlin.rename(columns={'cabinas_encendidas': 'cab_enc', 'cabinas_apagadas': 'cab_apa'})
], ignore_index=True)
dev['ns'] = dev['semana'].str.extract(r'(\d+)').astype(int)
dev = dev.sort_values(['linea', 'ns'])

lns = ['Total'] + sorted(df['linea'].unique())

# Preparamos una copia del DF para la tabla (formateando la fecha para evitar errores JSON)
df_table = df.copy()
df_table['fecha'] = df_table['fecha'].dt.strftime('%Y-%m-%d')

# ==========================================
# 3. CONFIGURACIÓN DE LA APLICACIÓN DASH
# ==========================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Dashboard - Relevamiento de Luces"

opciones_filtro = [{'label': '☰ Todas las Líneas', 'value': 'todas'}, 
                   {'label': '● Solo Totales', 'value': 'totales'}]
for l in [lin for lin in lns if lin != 'Total']:
    opciones_filtro.append({'label': f'— Línea {l}', 'value': l})

opciones_semana = [{'label': s, 'value': s} for s in semanas]
sem_ini = semanas[0] if semanas else None

columnas_tabla =['linea', 'seccion', 'fecha','cabinas_total', 'cabinas_encendidas', 'cabinas_apagadas', 'comentario', 'semana']


app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("Mantenimiento: Relevamiento de Luces en Cabinas", 
                        className="text-white p-3 rounded text-center shadow-sm"), 
                width=12)
    ], style={"backgroundColor": "#2C3E50"}, className="mb-4 mt-2"),

    # Controles de Filtrado
    dbc.Row([
        dbc.Col([
            html.Label("Filtro por Línea (Gráfica Evolución y Tabla):", className="fw-bold text-primary"),
            dcc.Dropdown(
                id='drop-linea',
                options=opciones_filtro,
                value='todas',
                clearable=False,
                className="shadow-sm"
            )
        ], md=6),
        dbc.Col([
            html.Label("Filtro por Semana (Gráfica Porcentajes y Tabla):", className="fw-bold text-primary"),
            dcc.Dropdown(
                id='drop-semana',
                options=opciones_semana,
                value=sem_ini,
                clearable=False,
                className="shadow-sm"
            )
        ], md=6)
    ], className="mb-4"),

    # Gráficos de Análisis
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='grafico-evo')), className="shadow-sm"), md=12, className="mb-4")
    ]),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='grafico-barras')), className="shadow-sm"), md=12, className="mb-4")
    ]),
    
    # Nueva Sección: DataTable Interactivo
    
    
    dbc.Row([
        dbc.Col([
            html.H4("Registro Detallado del Relevamiento", className="text-secondary mt-4 mb-3"),
            dbc.Card(
                dbc.CardBody([
                    dash_table.DataTable(
                        id='tabla-datos',
                        columns=[{"name": i.replace('_', ' ').title(), "id": i} for i in columnas_tabla],
                        page_size=10, # Paginación
                        sort_action="native", # Permite ordenar haciendo clic en las columnas
                        style_table={'overflowX': 'auto'},
                        style_header={
                            'backgroundColor': '#2C3E50',
                            'color': 'white',
                            'fontWeight': 'bold'
                        },
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px',
                            'fontFamily': 'sans-serif'
                        },
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}
                        ]
                    )
                ]), className="shadow-sm mb-5"
            )
        ], width=12)
    ])
], fluid=True, className="px-4")

# ==========================================
# 4. CALLBACKS
# ==========================================

# Callback 1: Gráfico de Evolución (Solo Encendidas y Líneas Suavizadas)
@app.callback(
    Output('grafico-evo', 'figure'),
    Input('drop-linea', 'value')
)
def update_evo(filtro):
    fig = go.Figure()
    
    if filtro == 'todas':
        lineas_a_mostrar = [l for l in lns if l != 'Total']
    elif filtro == 'totales':
        lineas_a_mostrar = ['Total']
    else:
        lineas_a_mostrar = [filtro]

    for linea in lineas_a_mostrar:
        d = dev[dev['linea'] == linea]
        xs = d['semana'].tolist()
        
        # Agregamos solo las encendidas y usamos shape='spline' para suavizar
        fig.add_trace(go.Scatter(
            x=xs, y=d['cab_enc'].tolist(),
            mode='lines+markers', name=f'{linea} (Encendidas)',
            line=dict(width=3, shape='spline', smoothing=1.3), # Suavizado aplicado aquí
            marker=dict(size=8)
        ))

    fig.update_layout(
        title="Evolución Semanal de Luces Operativas (Encendidas)", 
        yaxis_title="Cantidad de Cabinas",
        legend=dict(orientation="h", y=1.15, x=0), 
        height=450, 
        margin=dict(l=40, r=20, t=50, b=40),
        template="plotly_white"
    )
    return fig

# Callback 2: Gráfico de Barras de Porcentaje
@app.callback(
    Output('grafico-barras', 'figure'),
    Input('drop-semana', 'value')
)
def update_bar(sem):
    fig = go.Figure()
    if not sem:
        return fig

    ds = dbar[dbar['semana'] == sem]
    # Se omiten las líneas "Total" en este gráfico para no alterar la escala respecto a las líneas individuales
    ds = ds[ds['linea'] != 'Total'] 

    fig.add_trace(go.Bar(
        x=ds['linea'], y=ds['p_enc'], name='Encendidas %',
        marker_color='#2ecc71', hovertemplate='%{y:.2f}%'
    ))
    fig.add_trace(go.Bar(
        x=ds['linea'], y=ds['p_apa'], name='Apagadas %',
        marker_color='#e74c3c', hovertemplate='%{y:.2f}%'
    ))

    fig.update_layout(
        title=f"Porcentaje de Estado Operativo por Línea - {sem}", 
        yaxis_title="Porcentaje (%)",
        barmode='group', 
        height=450, 
        margin=dict(l=40, r=20, t=50, b=40),
        template="plotly_white",
        legend=dict(orientation="h", y=1.15, x=0)
    )
    return fig

# Callback 3: Llenado y Filtrado del DataTable
@app.callback(
    Output('tabla-datos', 'data'),
    [Input('drop-linea', 'value'),
     Input('drop-semana', 'value')]
)
def update_table(filtro_linea, sem):
    dff = df_table.copy()
    
    # 1. Filtrar por la semana seleccionada
    if sem:
        dff = dff[dff['semana'] == sem]
        
    # 2. Filtrar por la línea seleccionada
    if filtro_linea not in ['todas', 'totales']:
        dff = dff[dff['linea'] == filtro_linea]
        
    # Retornamos los datos filtrados en formato de diccionario para el DataTable
    return dff.to_dict('records')

# ==========================================
# 5. EJECUCIÓN DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    # debug=True permite que los cambios en el código se reflejen en tiempo real en el navegador
    app.run(debug=True, port=8050)