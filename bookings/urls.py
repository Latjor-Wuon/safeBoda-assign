"""
Booking URL patterns for SafeBoda Rwanda
All required booking endpoints with integrated workflow
"""
from django.urls import path
from . import enhanced_views as views

app_name = 'bookings'

urlpatterns = [
    # Core booking endpoints (Task 1 requirements)
    path('create/', views.CreateRideView.as_view(), name='create_ride'),
    path('<uuid:pk>/', views.RideDetailView.as_view(), name='ride_detail'),
    path('<uuid:pk>/status/', views.UpdateRideStatusView.as_view(), name='update_status'),
    path('<uuid:pk>/cancel/', views.CancelRideView.as_view(), name='cancel_ride'),
    path('active/', views.ActiveRidesView.as_view(), name='active_rides'),
    
    # Additional endpoints
    path('<uuid:pk>/rate/', views.rate_ride, name='rate_ride'),
    path('<uuid:pk>/location/', views.update_ride_location, name='update_location'),
    path('history/', views.RideHistoryView.as_view(), name='ride_history'),
]