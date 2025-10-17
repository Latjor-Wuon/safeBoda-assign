"""
WebSocket routing for SafeBoda Rwanda
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ride/(?P<ride_id>[0-9a-f-]+)/track/$', consumers.LocationTrackingConsumer.as_asgi()),
    re_path(r'ws/driver/location/$', consumers.DriverLocationConsumer.as_asgi()),
]