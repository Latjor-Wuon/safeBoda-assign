"""
URL configuration for government app
"""
from django.urls import path
from . import views

app_name = 'government'

urlpatterns = [
    # RTDA Compliance endpoints
    path('rtda/license/verify/', views.LicenseVerificationView.as_view(), name='license-verify'),
    path('rtda/vehicle/verify/', views.VehicleVerificationView.as_view(), name='vehicle-verify'),
    path('rtda/compliance/<int:driver_id>/', views.driver_compliance_check, name='compliance-check'),
    path('rtda/licenses/', views.RTDALicenseListView.as_view(), name='license-list'),
    path('rtda/licenses/<uuid:pk>/', views.RTDALicenseDetailView.as_view(), name='license-detail'),
    
    # Tax Management endpoints
    path('tax/calculate/', views.TaxCalculationView.as_view(), name='tax-calculate'),
    path('tax/records/', views.TaxRecordListView.as_view(), name='tax-records'),
    
    # Government Reporting endpoints
    path('reports/generate/', views.GenerateReportView.as_view(), name='generate-report'),
    path('reports/submit/', views.submit_report_to_government, name='submit-report'),
    path('reports/', views.GovernmentReportListView.as_view(), name='report-list'),
    
    # Emergency Services endpoints
    path('safety/incidents/', views.SafetyIncidentListView.as_view(), name='safety-incidents'),
    path('emergency/report/', views.report_emergency_incident, name='emergency-report'),
    path('emergency/services/', views.get_emergency_services, name='emergency-services'),
    path('emergency/contacts/', views.EmergencyContactListView.as_view(), name='emergency-contacts'),
]