from core.consumers import ApplyConsumer
from django.urls import  re_path

"""
This module defines the routing configuration for WebSocket connections in the project.

The `websocket_urlpatterns` list contains the URL patterns for WebSocket connections.
In this case, there is a single pattern defined: '^ws/$'. This pattern maps to the `ApplyConsumer`
class from the `core.consumers` module using the `re_path` function from `django.urls`.

Example usage:
    from django.urls import include, path
    from . import routing

    urlpatterns = [
        # ... other URL patterns ...
        path('websocket/', include(routing.websocket_urlpatterns)),
    ]
"""

websocket_urlpatterns = [
    re_path(r'^ws/$', ApplyConsumer.as_asgi()),
]
