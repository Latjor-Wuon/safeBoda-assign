"""
SafeBoda Rwanda URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# API URL patterns
api_v1_patterns = [
    path('auth/', include('authentication.urls')),
    path('bookings/', include('bookings.urls')),
    path('payments/', include('payments.urls')),
    path('locations/', include('locations.urls')),
    path('notifications/', include('notifications.urls')),
    path('government/', include('government.urls')),
    path('analytics/', include('analytics.urls')),
    path('monitoring/', include('monitoring.urls')),
]

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API
    path('api/', include(api_v1_patterns)),
    
    # OpenAPI Schema and Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health check (commented out for now)
    # path('health/', include('health_check.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Add debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Customize admin site
admin.site.site_header = "SafeBoda Rwanda Admin"
admin.site.site_title = "SafeBoda Rwanda"
admin.site.index_title = "Welcome to SafeBoda Rwanda Administration"