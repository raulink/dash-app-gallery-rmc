import dash

from lib.code_and_show import example_app


dash.register_page(
    __name__, description="Grafico Luces de cabinas"
)

filename = __name__.split("pages.")[1]


notes = """
#### Visualizador de Luces de cabinas

Este gráfico muestra el porcentaje de luces de cabinas en formato visual. Puedes interactuar con el gráfico para obtener detalle de cada linea por semanas.


##### Realizado por :
Realizado por [@Raul Mamani](https://github.com/raulink)

"""



layout = example_app(filename, notes=notes)
