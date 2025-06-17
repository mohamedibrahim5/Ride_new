# import os
# from channels.routing import ProtocolTypeRouter
# from django.core.asgi import get_asgi_application


# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
# http_application = get_asgi_application()


# async def lifespan_application(scope, receive, send):
#     if scope["type"] == "lifespan":
#         while True:
#             message = await receive()
#             if message["type"] == "lifespan.startup":
#                 await send({"type": "lifespan.startup.complete"})
#             elif message["type"] == "lifespan.shutdown":
#                 await send({"type": "lifespan.shutdown.complete"})
#                 return


# application = ProtocolTypeRouter(
#     {
#         "http": http_application,
#         "lifespan": lifespan_application,
#     }
# )

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
asgi_app=get_asgi_application()


import project.routing
from channels.routing import ProtocolTypeRouter, URLRouter
from core.middlewares import TokenAuthMiddleware


application = ProtocolTypeRouter({
    "http": asgi_app,
    # Just HTTP for now. (We can add other protocols later.)
    "websocket": TokenAuthMiddleware(
        URLRouter(
            # URLRouter just takes standard Django path() or url() entries.
            project.routing.websocket_urlpatterns
        ),
    ),

})
