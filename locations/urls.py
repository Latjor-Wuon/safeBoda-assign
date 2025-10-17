"""
URL configuration for locations app - Enhanced Real-time Tracking
"""
from django.urls import path
from . import realtime_views

app_name = 'locations'

urlpatterns = [
    # Enhanced real-time tracking endpoints (Task 1 requirements)
    path('tracking/<uuid:booking_id>/', realtime_views.RealTimeTrackingView.as_view(), name='realtime-tracking'),
    
    # Location management with WebSocket integration
    path('update/', realtime_views.UpdateLocationView.as_view(), name='update-location'),
    path('nearby-drivers/', realtime_views.NearbyDriversView.as_view(), name='nearby-drivers'),
    path('tracking/<uuid:booking_id>/start/', realtime_views.start_ride_tracking, name='start-tracking'),
]