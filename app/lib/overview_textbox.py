from dash import dcc
import dash_bootstrap_components as dbc

content = """
#### Bienvenido a la galería de aplicaciones del DM! 

Aqui se encuentran las visualizaciones realizadas para el Departamento de Mantenimiento


La pagina principal de acceso se encuentra en: 
[lineas.miteleferico.bo](http://lineas.miteleferico.bo).

Las visualizaciones fueron realizadas por Raul Mamani@2026 .
"""

card = dbc.Card(
    dcc.Markdown(content, link_target="_blank"),
    className="shadow-sm p-3",
)
