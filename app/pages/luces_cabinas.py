import dash

from lib.code_and_show import example_app


dash.register_page(
    __name__, description="Grafico Luces de cabinas"
)

filename = __name__.split("pages.")[1]


notes = """
#### Visualizador de Luces de cabinas

Este gráfico muestra los ingresos de luces de cabinas en un formato visual. Puedes interactuar con el gráfico para obtener más detalles sobre cada punto de datos.


##### Realizado por :
Realizado por [@Raul Mamani](https://github.com/raulink)

"""



layout = example_app(filename, notes=notes)
