"""
URL configuration for monitoring app
"""
from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Health check endpoints
    path('health/detailed/', views.detailed_health_check, name='detailed-health-check'),
    
    # Monitoring endpoints
    path('metrics/', views.MetricsView.as_view(), name='system-metrics'),
    path('logs/', views.application_logs, name='application-logs'),
    
    # Admin endpoints
    path('backup/trigger/', views.trigger_backup, name='trigger-backup'),
    path('system/status/', views.SystemStatusView.as_view(), name='system-status'),
    path('maintenance/enable/', views.enable_maintenance_mode, name='enable-maintenance'),
]