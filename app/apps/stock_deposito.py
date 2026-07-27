import dash
from dash import dash_table, dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.dash_table.Format import Format, Scheme  # NUEVA IMPORTACIÓN PARA EL FORMATO
import pandas as pd
import io
import plotly.express as px
from sqlalchemy import create_engine

# -----------------------------------------------------------------------------
# 0. FUNCIONES DE AYUDA (HELPERS)
# -----------------------------------------------------------------------------
def formato_latino(valor):
    """
    Convierte un valor numérico a formato string con 1 decimal, 
    separador de miles '.' y separador decimal ','
    Ejemplo: 1234.56 -> "1.234,6"
    """
    try:
        # Formateo estándar US con 1 decimal (ej. "1,234.6")
        num_str = f"{float(valor):,.1f}"
        # Intercambio de puntuación
        return num_str.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "0,0"

# -----------------------------------------------------------------------------
# 1. CONEXIÓN Y CONSULTAS A LAS BASES DE DATOS (CON SQLALCHEMY)
# -----------------------------------------------------------------------------
def obtener_inventario_detallado():
    db_uri = "mysql+pymysql://mantto:Sistemas0@lineas.miteleferico.bo:3307/sgmateriales"
    
    sql_query = """
    SELECT
        a.id_eetc AS id_eetc_articulo,
        a.id_dopp AS id_dopp_articulo,
        a.name AS nombre_articulo,
        aw.quantity,
        w.name AS nombre_deposito,
        s.name AS nombre_estacion,
        l.name AS nombre_linea
    FROM article_warehouse aw
    INNER JOIN articles a ON aw.article_id = a.id
    INNER JOIN warehouses w ON aw.warehouse_id = w.id
    INNER JOIN stations s ON w.station_id = s.id
    INNER JOIN `lines` l ON s.line_id = l.id
    WHERE quantity > 0
    ORDER BY s.id, aw.warehouse_id, a.id_eetc;
    """
    
    try:
        engine = create_engine(db_uri)
        df = pd.read_sql_query(sql_query, engine)
        engine.dispose()
        return df
    except Exception as e:
        print(f"Error al conectar o consultar inventario en MySQL: {e}")
        return pd.DataFrame(columns=[
            "id_eetc_articulo", "id_dopp_articulo", "nombre_articulo", 
            "quantity", "nombre_deposito", "nombre_estacion", "nombre_linea"
        ])

def obtener_precios():
    pg_uri = "postgresql+psycopg2://postgres:postgres@192.168.100.50:5433/ingresos_db"
    
    sql_precios = """
    SELECT DISTINCT ON (s.codigo)
           s.codigo,
           s.id_proveedor,
           s.item,
           s.punitario
    FROM   salidas s
    WHERE  s.codigo IS NOT NULL
    ORDER  BY s.codigo;
    """
    
    try:
        engine = create_engine(pg_uri)
        df = pd.read_sql_query(sql_precios, engine)
        engine.dispose()
        return df
    except Exception as e:
        print(f"Error al conectar o consultar precios en PostgreSQL: {e}")
        return pd.DataFrame(columns=["codigo", "id_proveedor", "item", "punitario"])

# Carga y cruce inicial
df_inventario = obtener_inventario_detallado()
df_precios = obtener_precios()

df_consolidado = pd.merge(
    df_inventario, 
    df_precios[['codigo', 'punitario']], 
    left_on='id_eetc_articulo', 
    right_on='codigo', 
    how='left'
)
df_consolidado.drop(columns=['codigo'], inplace=True, errors='ignore')

# Calcular el Precio Total de forma segura
df_consolidado['punitario'] = pd.to_numeric(df_consolidado['punitario'], errors='coerce').fillna(0)
df_consolidado['quantity'] = pd.to_numeric(df_consolidado['quantity'], errors='coerce').fillna(0)
df_consolidado['precio_total'] = df_consolidado['punitario'] * df_consolidado['quantity']


# -----------------------------------------------------------------------------
# 2. CONFIGURACIÓN DE LA APLICACIÓN DASH Y FORMATO DE COLUMNAS
# -----------------------------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Inventario por Estaciones"

# Definición del formato específico: 1.000,0
formato_numerico = Format(
    scheme=Scheme.fixed,
    precision=1,
    group=True,
    groups=3,
    group_delimiter='.',
    decimal_delimiter=','
)

columnas_visibles = [
    {"name": "Línea", "id": "nombre_linea"},
    {"name": "Estación", "id": "nombre_estacion"},
    {"name": "Depósito", "id": "nombre_deposito"},
    {"name": "Código EETC", "id": "id_eetc_articulo"},
    {"name": "Código DOPP", "id": "id_dopp_articulo"},
    {"name": "Artículo", "id": "nombre_articulo"},
    {"name": "Cantidad", "id": "quantity", "type": "numeric", "format": formato_numerico},
    {"name": "Precio Unitario", "id": "punitario", "type": "numeric", "format": formato_numerico},
    {"name": "Precio Total", "id": "precio_total", "type": "numeric", "format": formato_numerico},
]

# -----------------------------------------------------------------------------
# 3. DISEÑO DE LA INTERFAZ (Layout)
# -----------------------------------------------------------------------------
app.layout = dbc.Container([
    
    dbc.Row([
        dbc.Col(html.H2("Consulta de Inventario por Estación y Línea", className="text-center my-4 text-dark"), width=12)
    ]),
    
    dbc.Row([
        # Panel de Filtros
        dbc.Col([
            html.Div([
                html.Label("Línea:", className="fw-bold text-secondary mb-1"),
                dcc.Dropdown(
                    id="filtro-linea",
                    options=[{"label": l, "value": l} for l in df_consolidado["nombre_linea"].dropna().unique()],
                    placeholder="Todas las líneas...",
                    multi=True,
                    className="mb-3"
                ),
                
                html.Label("Estación:", className="fw-bold text-secondary mb-1"),
                dcc.Dropdown(
                    id="filtro-estacion",
                    placeholder="Todas las estaciones...",
                    multi=True,
                    className="mb-3",
                    options=[] 
                ),
                
                html.Hr(),
                
                html.Label("Registros por página:", className="fw-bold text-secondary mb-1"),
                dcc.Dropdown(
                    id="selector-registros",
                    options=[
                        {"label": "10 registros", "value": 10},
                        {"label": "20 registros", "value": 20},
                        {"label": "50 registros", "value": 50},
                        {"label": "100 registros", "value": 100}
                    ],
                    value=20,
                    clearable=False,
                    className="mb-4"
                ),
                
                dbc.Button("Exportar a Excel", id="btn-exportar", color="success", className="w-100 fw-bold"),
                dcc.Download(id="download-excel")
                
            ], className="bg-light p-3 rounded shadow-sm mb-4")
        ], lg=3, md=12),
        
        # Panel Principal (KPIs y Gráficos)
        dbc.Col([
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("Artículos Diferentes", className="card-subtitle text-muted text-center mb-1"),
                        html.H3(id="kpi-articulos-unicos", className="text-center text-primary fw-bold")
                    ])
                ], className="border-start border-primary border-4 shadow-sm mb-3"), width=4),
                
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("Stock Físico Total", className="card-subtitle text-muted text-center mb-1"),
                        html.H3(id="kpi-total-stock", className="text-center text-success fw-bold")
                    ])
                ], className="border-start border-success border-4 shadow-sm mb-3"), width=4),

                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("Valorización Total", className="card-subtitle text-muted text-center mb-1"),
                        html.H3(id="kpi-valor-total", className="text-center text-info fw-bold")
                    ])
                ], className="border-start border-info border-4 shadow-sm mb-3"), width=4),
            ]),
            
            # Fila de Gráficos
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dcc.Graph(id="grafico-dinamico")
                    ], className="bg-white p-2 rounded shadow-sm border mb-3")
                ], lg=6, md=12),
                
                dbc.Col([
                    html.Div([
                        dcc.Graph(id="grafico-total-linea")
                    ], className="bg-white p-2 rounded shadow-sm border mb-3")
                ], lg=6, md=12)
            ])
        ], lg=9, md=12)
    ]),
    
    # Tabla de datos
    dbc.Row([
        dbc.Col([
            html.Div([
                dash_table.DataTable(
                    id="tabla-inventario",
                    columns=columnas_visibles,
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={
                        "textAlign": "left",
                        "padding": "10px 14px",
                        "fontFamily": "Segoe UI, sans-serif",
                        "fontSize": "14px"
                    },
                    style_header={
                        "backgroundColor": "#f8f9fa",
                        "color": "#495057",
                        "fontWeight": "600",
                        "borderBottom": "2px solid #dee2e6"
                    },
                    style_data={"borderBottom": "1px solid #e9ecef"},
                    style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#fdfdfd"}]
                )
            ], className="bg-white p-3 rounded shadow-sm border")
        ], width=12)
    ], className="mt-2 mb-5")
    
], fluid=True, style={"backgroundColor": "#f4f6f9", "minHeight": "100vh"})

# -----------------------------------------------------------------------------
# 4. INTERACTIVIDAD Y ACTUALIZACIÓN (Callbacks)
# -----------------------------------------------------------------------------

@app.callback(
    Output("filtro-estacion", "options"),
    [Input("filtro-linea", "value")]
)
def set_estaciones_options(lineas_seleccionadas):
    if not lineas_seleccionadas:
        estaciones = df_consolidado["nombre_estacion"].dropna().unique()
    else:
        estaciones = df_consolidado[df_consolidado["nombre_linea"].isin(lineas_seleccionadas)]["nombre_estacion"].dropna().unique()
    return [{"label": est, "value": est} for est in estaciones]

@app.callback(
    Output("tabla-inventario", "page_size"),
    [Input("selector-registros", "value")]
)
def actualizar_paginacion(tamanio_pagina):
    return tamanio_pagina

@app.callback(
    [Output("tabla-inventario", "data"),
     Output("kpi-articulos-unicos", "children"),
     Output("kpi-total-stock", "children"),
     Output("kpi-valor-total", "children"),
     Output("grafico-dinamico", "figure"),
     Output("grafico-total-linea", "figure")],
    [Input("filtro-linea", "value"),
     Input("filtro-estacion", "value")]
)
def actualizar_dashboard(lineas, estaciones):
    df_filtrado = df_consolidado.copy()
    
    if lineas:
        df_filtrado = df_filtrado[df_filtrado["nombre_linea"].isin(lineas)]
    if estaciones:
        df_filtrado = df_filtrado[df_filtrado["nombre_estacion"].isin(estaciones)]
        
    articulos_unicos = df_filtrado["nombre_articulo"].nunique()
    total_stock = df_filtrado["quantity"].sum() if not df_filtrado.empty else 0
    valor_total = df_filtrado["precio_total"].sum() if not df_filtrado.empty else 0
    
    # Gráfico 1: Treemap de Cantidades
    if not df_filtrado.empty:
        fig1 = px.treemap(
            df_filtrado, 
            path=[px.Constant("Inventario Global"), 'nombre_linea', 'nombre_estacion', 'nombre_deposito'], 
            values='quantity',
            color='quantity',
            color_continuous_scale='Blues',
            title='Distribución de Cantidades Físicas'
        )
        # Se establece la puntuación en el layout de Plotly y márgenes
        fig1.update_layout(margin=dict(t=40, l=10, r=10, b=10), separators=",.")
        # Se asegura que la cantidad también muestre 1 decimal
        fig1.update_traces(textinfo="label+value", texttemplate="%{label}<br>%{value:,.1f}")
    else:
        fig1 = px.scatter(title="Sin datos para mostrar")
        
    # Gráfico 2: Barras de Valor Total por Línea
    if not df_filtrado.empty:
        df_group_linea = df_filtrado.groupby('nombre_linea', as_index=False)['precio_total'].sum()
        fig2 = px.bar(
            df_group_linea,
            x='nombre_linea',
            y='precio_total',
            title='Valor Total del Inventario por Línea',
            labels={'nombre_linea': 'Línea', 'precio_total': 'Precio Total'},
            color='precio_total',
            color_continuous_scale='Teal',
            text='precio_total' # Añade el texto a la barra
        )
        # Formato numérico en la gráfica (decimal coma, miles punto)
        fig2.update_layout(margin=dict(t=40, l=10, r=10, b=10), separators=",.")
        fig2.update_traces(texttemplate='%{text:,.1f}', textposition='outside')
    else:
        fig2 = px.scatter(title="Sin datos para mostrar")
    
    # Retornar datos de la tabla, y los KPIs ya formateados con nuestro helper
    return (
        df_filtrado.to_dict("records"), 
        formato_latino(articulos_unicos), 
        formato_latino(total_stock), 
        formato_latino(valor_total), 
        fig1, 
        fig2
    )

@app.callback(
    Output("download-excel", "data"),
    Input("btn-exportar", "n_clicks"),
    State("tabla-inventario", "data"),
    prevent_initial_call=True
)
def generar_excel(n_clicks, data_tabla):
    if not data_tabla:
        return dash.no_update
        
    df_export = pd.DataFrame(data_tabla)
    
    mapa_columnas = {col["id"]: col["name"] for col in columnas_visibles}
    columnas_presentes = [col for col in mapa_columnas.keys() if col in df_export.columns]
    df_export = df_export[columnas_presentes].rename(columns=mapa_columnas)
    
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df_export.to_excel(writer, index=False, sheet_name='Reporte_Inventario')
    
    workbook = writer.book
    worksheet = writer.sheets['Reporte_Inventario']
    
    # Se añade la propiedad num_format para mantener 1 decimal e indicar el separador de miles.
    # En Excel, el formato "#,##0.0" se adapta automáticamente a la configuración regional del PC del usuario.
    formato_base = workbook.add_format({'font_name': 'Arial Narrow', 'font_size': 11})
    formato_numero_base = workbook.add_format({'font_name': 'Arial Narrow', 'font_size': 11, 'num_format': '#,##0.0'})
    formato_negrita = workbook.add_format({'font_name': 'Arial Narrow', 'font_size': 11, 'bold': True})
    
    worksheet.set_column('A:E', None, formato_base)
    worksheet.set_column('A:A', None, formato_negrita)
    worksheet.set_column('F:F', 250)
    
    # Aplicamos el formato numérico a las columnas de Cantidad, P.Unitario y P.Total (Columnas G, H, I)
    worksheet.set_column('G:I', 15, formato_numero_base)
    
    writer.close()
    output.seek(0)
    
    return dcc.send_bytes(output.getvalue(), "Reporte_Inventario.xlsx")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')