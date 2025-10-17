"""
URL patterns for SafeBoda Rwanda testing framework
"""

from django.urls import path
from .views import (
    HealthCheckView, SeedTestDataView, CoverageReportView,
    LoadTestingView, SecurityScanView
)

app_name = 'testing_framework'

urlpatterns = [
    # Testing API endpoints as specified in requirements
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('seed-data/', SeedTestDataView.as_view(), name='seed_data'),
    path('coverage-report/', CoverageReportView.as_view(), name='coverage_report'),
    path('simulate-load/', LoadTestingView.as_view(), name='simulate_load'),
    path('security-scan/', SecurityScanView.as_view(), name='security_scan'),
]