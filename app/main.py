from starlette.middleware.wsgi import WSGIMiddleware
from app import server  # Importa la instancia Flask subyacente

application = WSGIMiddleware(server)  # Convierte la aplicación Flask a ASGI
