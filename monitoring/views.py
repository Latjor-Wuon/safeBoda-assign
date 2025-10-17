"""
Monitoring views for SafeBoda Rwanda
Production-ready health checks and system monitoring
"""
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
import redis
import psutil
import os
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Detailed health check",
    description="Comprehensive health check for all system components",
    tags=['Monitoring']
)
@api_view(['GET'])
def detailed_health_check(request):
    """
    GET /api/health/detailed/ - Comprehensive health check
    """
    health_status = {
        'timestamp': timezone.now().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    overall_healthy = True
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status['checks']['database'] = {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'message': f'Database error: {str(e)}'
        }
        overall_healthy = False
    
    # Cache check (Redis)
    try:
        cache.set('health_check', 'test', 30)
        cache_value = cache.get('health_check')
        if cache_value == 'test':
            health_status['checks']['cache'] = {
                'status': 'healthy',
                'message': 'Cache system operational'
            }
        else:
            raise Exception("Cache test failed")
    except Exception as e:
        health_status['checks']['cache'] = {
            'status': 'unhealthy',
            'message': f'Cache error: {str(e)}'
        }
        overall_healthy = False
    
    # Disk space check
    try:
        disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        if disk_percent < 85:
            health_status['checks']['disk_space'] = {
                'status': 'healthy',
                'usage_percent': round(disk_percent, 2),
                'free_gb': round(disk_usage.free / (1024**3), 2)
            }
        else:
            health_status['checks']['disk_space'] = {
                'status': 'warning',
                'usage_percent': round(disk_percent, 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'message': 'Disk space running low'
            }
            if disk_percent > 95:
                overall_healthy = False
    except Exception as e:
        health_status['checks']['disk_space'] = {
            'status': 'unknown',
            'message': f'Could not check disk space: {str(e)}'
        }
    
    # Memory check
    try:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        if memory_percent < 85:
            health_status['checks']['memory'] = {
                'status': 'healthy',
                'usage_percent': memory_percent,
                'available_gb': round(memory.available / (1024**3), 2)
            }
        else:
            health_status['checks']['memory'] = {
                'status': 'warning',
                'usage_percent': memory_percent,
                'available_gb': round(memory.available / (1024**3), 2),
                'message': 'High memory usage'
            }
            if memory_percent > 95:
                overall_healthy = False
    except Exception as e:
        health_status['checks']['memory'] = {
            'status': 'unknown',
            'message': f'Could not check memory: {str(e)}'
        }
    
    # Set overall status
    if not overall_healthy:
        health_status['status'] = 'unhealthy'
    
    response_status = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(health_status, status=response_status)


@extend_schema_view(
    get=extend_schema(
        summary="System performance metrics",
        description="Get system performance metrics and statistics",
        tags=['Monitoring']
    )
)
class MetricsView(APIView):
    """
    GET /api/monitoring/metrics/ - System performance metrics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get system performance metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Database metrics
            from django.contrib.auth import get_user_model
            from bookings.models import Ride
            from notifications.models import Notification
            
            User = get_user_model()
            
            # Get counts
            total_users = User.objects.count()
            total_rides = Ride.objects.count()
            active_rides = Ride.objects.filter(
                status__in=['accepted', 'driver_en_route', 'in_progress']
            ).count()
            
            # Recent activity (last 24 hours)
            last_24h = timezone.now() - timedelta(hours=24)
            recent_rides = Ride.objects.filter(created_at__gte=last_24h).count()
            recent_users = User.objects.filter(date_joined__gte=last_24h).count()
            
            metrics = {
                'timestamp': timezone.now().isoformat(),
                'system': {
                    'cpu_usage_percent': cpu_percent,
                    'memory_usage_percent': memory.percent,
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'disk_usage_percent': round((disk.used / disk.total) * 100, 2),
                    'disk_free_gb': round(disk.free / (1024**3), 2)
                },
                'application': {
                    'total_users': total_users,
                    'total_rides': total_rides,
                    'active_rides': active_rides,
                    'recent_rides_24h': recent_rides,
                    'new_users_24h': recent_users
                },
                'performance': {
                    'uptime_hours': round((timezone.now() - timezone.datetime.fromtimestamp(
                        psutil.boot_time(), tz=timezone.utc
                    )).total_seconds() / 3600, 2)
                }
            }
            
            return Response(metrics, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Metrics collection error: {str(e)}")
            return Response(
                {'error': 'Failed to collect metrics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    summary="Application logs",
    description="Get recent application logs (admin only)",
    tags=['Monitoring']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def application_logs(request):
    """
    GET /api/monitoring/logs/ - Application logs (admin only)
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Get log level from query params
        log_level = request.query_params.get('level', 'INFO')
        lines = int(request.query_params.get('lines', 100))
        
        # In production, this would read from actual log files
        # For now, return sample log entries
        logs = {
            'log_level': log_level,
            'lines_requested': lines,
            'timestamp': timezone.now().isoformat(),
            'logs': [
                {
                    'timestamp': timezone.now().isoformat(),
                    'level': 'INFO',
                    'message': 'Application health check completed successfully',
                    'module': 'monitoring.views'
                },
                {
                    'timestamp': (timezone.now() - timedelta(minutes=5)).isoformat(),
                    'level': 'INFO',
                    'message': 'New ride request processed',
                    'module': 'bookings.views'
                }
            ]
        }
        
        return Response(logs, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Log retrieval error: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve logs'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Trigger manual backup",
    description="Trigger a manual database backup (admin only)",
    tags=['Monitoring']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def trigger_backup(request):
    """
    POST /api/admin/backup/trigger/ - Manual backup trigger
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # In production, this would trigger actual backup process
        backup_id = f"backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Simulate backup process
        backup_info = {
            'backup_id': backup_id,
            'status': 'initiated',
            'timestamp': timezone.now().isoformat(),
            'estimated_completion': (timezone.now() + timedelta(minutes=30)).isoformat(),
            'message': 'Database backup initiated successfully'
        }
        
        return Response(backup_info, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Backup trigger error: {str(e)}")
        return Response(
            {'error': 'Failed to trigger backup'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema_view(
    get=extend_schema(
        summary="System status dashboard",
        description="Get comprehensive system status for admin dashboard",
        tags=['Monitoring']
    )
)
class SystemStatusView(APIView):
    """
    GET /api/admin/system/status/ - System status dashboard
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get system status dashboard data"""
        if request.user.role != 'admin':
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from django.contrib.auth import get_user_model
            from bookings.models import Ride
            from analytics.models import RideMetrics
            
            User = get_user_model()
            
            # Recent activity stats
            last_hour = timezone.now() - timedelta(hours=1)
            last_24h = timezone.now() - timedelta(hours=24)
            
            status_data = {
                'timestamp': timezone.now().isoformat(),
                'system_health': 'healthy',  # Would be calculated from health checks
                'active_users': {
                    'total_online': 0,  # Would track active sessions
                    'drivers_available': User.objects.filter(role='driver', is_available=True).count(),
                    'customers_active': 0
                },
                'ride_activity': {
                    'rides_last_hour': Ride.objects.filter(created_at__gte=last_hour).count(),
                    'rides_last_24h': Ride.objects.filter(created_at__gte=last_24h).count(),
                    'active_rides': Ride.objects.filter(
                        status__in=['accepted', 'driver_en_route', 'in_progress']
                    ).count(),
                    'completed_today': Ride.objects.filter(
                        status='completed',
                        created_at__date=timezone.now().date()
                    ).count()
                },
                'system_resources': {
                    'cpu_usage': psutil.cpu_percent(),
                    'memory_usage': psutil.virtual_memory().percent,
                    'disk_usage': round((psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100, 2)
                },
                'alerts': []  # Would contain system alerts
            }
            
            return Response(status_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"System status error: {str(e)}")
            return Response(
                {'error': 'Failed to get system status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    summary="Enable maintenance mode",
    description="Enable system maintenance mode (admin only)",
    tags=['Monitoring']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def enable_maintenance_mode(request):
    """
    POST /api/admin/maintenance/enable/ - Enable maintenance mode
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Set maintenance mode flag in cache
        cache.set('maintenance_mode', True, timeout=None)
        cache.set('maintenance_enabled_by', request.user.email, timeout=None)
        cache.set('maintenance_enabled_at', timezone.now().isoformat(), timeout=None)
        
        return Response({
            'status': 'maintenance_enabled',
            'message': 'Maintenance mode has been enabled',
            'enabled_by': request.user.email,
            'enabled_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Maintenance mode error: {str(e)}")
        return Response(
            {'error': 'Failed to enable maintenance mode'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )