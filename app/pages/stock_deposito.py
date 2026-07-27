import dash

from lib.code_and_show import example_app


dash.register_page(
    __name__, description="Stocks de Almacenes de Lineas."
)

filename = __name__.split("pages.")[1]


notes = """
##### Reporte de Almacenes de lineas:
Extraido de SG Materiales, este reporte muestra los stocks de los almacenes de lineas, con sus respectivos precios unitarios y totales.

"""



layout = example_app(filename, notes=notes)
