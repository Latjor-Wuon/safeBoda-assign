"""
Administrative Reporting URLs
URL patterns for government compliance and administrative reporting endpoints
"""
from django.urls import path
from .admin_views import (
    AdminRideReportsView,
    AdminDriverReportsView,
    government_compliance_status,
    export_admin_report
)

app_name = 'analytics_admin'

urlpatterns = [
    # Administrative ride reports
    path(
        'reports/rides/',
        AdminRideReportsView.as_view(),
        name='admin_ride_reports'
    ),
    
    # Driver performance reports
    path(
        'reports/drivers/',
        AdminDriverReportsView.as_view(),
        name='admin_driver_reports'
    ),
    
    # Government compliance status
    path(
        'compliance/status/',
        government_compliance_status,
        name='government_compliance_status'
    ),
    
    # Export reports
    path(
        'reports/export/',
        export_admin_report,
        name='export_admin_report'
    ),
]