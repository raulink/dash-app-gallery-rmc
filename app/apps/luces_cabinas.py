import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, dash_table
from dotenv import load_dotenv
import os

load_dotenv()

# ==========================================
# 1. FUNCIÓN CENTRAL DE EXTRACCIÓN Y PROCESAMIENTO
# ==========================================
# Al encapsular esto en una función, cada vez que se ejecuta se hace
# la consulta a la BD y, al terminar, se destruyen los DataFrames locales.
def obtener_y_procesar_datos():
    MYSQL_USER =  os.getenv('MYSQL_USER') or 'zona1'
    MYSQL_PASS = os.getenv('MYSQL_PASS') or 'Sistemas0.'
    MYSQL_HOST = os.getenv('MYSQL_HOST') or '192.168.100.60'
    MYSQL_DB = os.getenv('MYSQL_DB') or 'opmt2'

    # Crear el motor de conexión
    engine = create_engine(f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}/{MYSQL_DB}")

    # Consulta SQL
    query = "SELECT * FROM `relevamiento_luces`"
    df = pd.read_sql(query, engine)
    
    # Liberar el motor de base de datos tras la consulta
    engine.dispose()

    # Procesamiento de datos
    df['linea'] = df['linea'].fillna('Desconocida')
    df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True)
    df['semana'] = 'Semana ' + df['fecha'].dt.isocalendar().week.astype(str)

    weeks = df['semana'].unique()

    # Generador de datos (por si la BD tiene pocos registros históricos)
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

    # Formatear la copia del DF para la tabla (evitando errores JSON)
    df_table = df.copy()
    df_table['fecha'] = df_table['fecha'].dt.strftime('%Y-%m-%d')

    # Devolvemos un diccionario serializable para guardarlo en el dcc.Store
    return {
        'df_table': df_table.to_dict('records'),
        'dev': dev.to_dict('records'),
        'dbar': dbar.to_dict('records'),
        'lns': lns,
        'semanas': semanas
    }

# ==========================================
# 2. CONFIGURACIÓN DE LA APLICACIÓN DASH
# ==========================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Dashboard - Relevamiento de Luces"

columnas_tabla =['linea', 'seccion', 'fecha','cabinas_total', 'cabinas_encendidas', 'cabinas_apagadas', 'comentario', 'semana']

app.layout = dbc.Container([
    # Store para guardar los datos de forma invisible en el navegador
    dcc.Store(id='store-datos'),

    dbc.Row([
        dbc.Col(html.H2("Mantenimiento: Relevamiento de Luces en Cabinas", 
                        className="text-white p-3 rounded text-center shadow-sm m-0"), 
                md=10, xs=12),
        dbc.Col(dbc.Button("🔄 Refrescar Datos", id="btn-refrescar", color="info", className="w-100 fw-bold shadow-sm h-100 text-white"), 
                md=2, xs=12, className="d-flex align-items-center mt-3 mt-md-0")
    ], style={"backgroundColor": "#2C3E50", "padding": "10px", "borderRadius": "5px"}, className="mb-4 mt-2 d-flex align-items-stretch"),

    # Controles de Filtrado
    dbc.Row([
        dbc.Col([
            html.Label("Filtro por Línea (Gráfica Evolución y Tabla):", className="fw-bold text-primary"),
            dcc.Dropdown(
                id='drop-linea',
                options=[], # Se llenará dinámicamente
                value='todas',
                clearable=False,
                className="shadow-sm"
            )
        ], md=6),
        dbc.Col([
            html.Label("Filtro por Semana (Gráfica Porcentajes y Tabla):", className="fw-bold text-primary"),
            dcc.Dropdown(
                id='drop-semana',
                options=[], # Se llenará dinámicamente
                value=None,
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
    
    # DataTable Interactivo
    dbc.Row([
        dbc.Col([
            html.H4("Registro Detallado del Relevamiento", className="text-secondary mt-4 mb-3"),
            dbc.Card(
                dbc.CardBody([
                    dash_table.DataTable(
                        id='tabla-datos',
                        columns=[{"name": i.replace('_', ' ').title(), "id": i} for i in columnas_tabla],
                        page_size=10,
                        sort_action="native",
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
# 3. CALLBACKS
# ==========================================

# Callback 0: Extracción Principal (Se ejecuta al abrir la app o presionar el botón)
@app.callback(
    [Output('store-datos', 'data'),
     Output('drop-linea', 'options'),
     Output('drop-semana', 'options'),
     Output('drop-semana', 'value')],
    [Input('btn-refrescar', 'n_clicks')],
    [State('drop-semana', 'value')]
)
def actualizar_base_datos(n_clicks, semana_actual):
    # Esto "destruye" el dataframe anterior porque reconstruye uno nuevo
    datos = obtener_y_procesar_datos()
    
    opciones_filtro = [{'label': '☰ Todas las Líneas', 'value': 'todas'}, 
                       {'label': '● Solo Totales', 'value': 'totales'}]
    for l in [lin for lin in datos['lns'] if lin != 'Total']:
        opciones_filtro.append({'label': f'— Línea {l}', 'value': l})
        
    opciones_semana = [{'label': s, 'value': s} for s in datos['semanas']]
    
    # Mantenemos la semana seleccionada si sigue existiendo tras la actualización
    sem_value = semana_actual if semana_actual in datos['semanas'] else (datos['semanas'][0] if datos['semanas'] else None)
    
    return datos, opciones_filtro, opciones_semana, sem_value

# Callback 1: Gráfico de Evolución
@app.callback(
    Output('grafico-evo', 'figure'),
    [Input('drop-linea', 'value'),
     Input('store-datos', 'data')]
)
def update_evo(filtro, datos):
    fig = go.Figure()
    if not datos: # Prevenir actualización si los datos aún no se cargan
        return fig
        
    dev = pd.DataFrame(datos['dev'])
    lns = datos['lns']
    
    if filtro == 'todas':
        lineas_a_mostrar = [l for l in lns if l != 'Total']
    elif filtro == 'totales':
        lineas_a_mostrar = ['Total']
    else:
        lineas_a_mostrar = [filtro]

    for linea in lineas_a_mostrar:
        d = dev[dev['linea'] == linea]
        xs = d['semana'].tolist()
        
        fig.add_trace(go.Scatter(
            x=xs, y=d['cab_enc'].tolist(),
            mode='lines+markers', name=f'{linea} (Encendidas)',
            line=dict(width=3, shape='spline', smoothing=1.3),
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
    [Input('drop-semana', 'value'),
     Input('store-datos', 'data')]
)
def update_bar(sem, datos):
    fig = go.Figure()
    if not sem or not datos:
        return fig

    dbar = pd.DataFrame(datos['dbar'])
    ds = dbar[dbar['semana'] == sem]    
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
     Input('drop-semana', 'value'),
     Input('store-datos', 'data')]
)
def update_table(filtro_linea, sem, datos):
    if not datos:
        return []
        
    dff = pd.DataFrame(datos['df_table'])
    
    if sem:
        dff = dff[dff['semana'] == sem]
        
    if filtro_linea not in ['todas', 'totales']:
        dff = dff[dff['linea'] == filtro_linea]
        
    return dff.to_dict('records')

# ==========================================
# 4. EJECUCIÓN DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    app.run(debug=True, port=8050)