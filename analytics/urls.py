"""
Analytics URL patterns for SafeBoda Rwanda
All 6 required analytics endpoints + admin reporting endpoints
"""
from django.urls import path, include
from . import views

app_name = 'analytics'

urlpatterns = [
    # Core analytics endpoints (6 required)
    path('rides/patterns/', views.RideSummaryAnalyticsView.as_view(), name='ride_summary'),
    path('revenue/', views.RevenueAnalyticsView.as_view(), name='revenue'),
    path('drivers/performance/', views.DriverPerformanceAnalyticsView.as_view(), name='driver_performance'),
    path('traffic/hotspots/', views.PopularRoutesAnalyticsView.as_view(), name='popular_routes'),
    path('users/behavior/', views.CustomerInsightsAnalyticsView.as_view(), name='customer_insights'),
    path('reports/generate/', views.TimePatternsAnalyticsView.as_view(), name='time_patterns'),
    
    # Administrative reporting (government compliance)
    path('admin/', include('analytics.admin_urls')),
    
    # Report management
    path('generate-report/', views.ReportGenerationView.as_view(), name='generate_report'),
    path('reports/', views.AnalyticsReportListView.as_view(), name='report_list'),
    path('reports/<uuid:pk>/', views.AnalyticsReportDetailView.as_view(), name='report_detail'),
    
    # Dashboard
    path('dashboard/', views.analytics_dashboard, name='dashboard')
]