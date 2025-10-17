"""
Location and real-time tracking views for SafeBoda Rwanda
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Location, LocationUpdate
from bookings.models import Ride
from .serializers import LocationSerializer, LocationUpdateSerializer
from .services import LocationTrackingService
import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    get=extend_schema(
        summary="Get real-time tracking for booking",
        description="Get real-time location updates for a specific booking",
        tags=['Real-time Tracking']
    )
)
class RealTimeTrackingView(APIView):
    """
    GET /api/realtime/tracking/{booking_id}/ - Real-time location updates
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, booking_id):
        """Get real-time tracking data for a booking"""
        try:
            ride = get_object_or_404(Ride, id=booking_id)
            
            # Check if user has permission to view this ride
            if not (ride.customer == request.user or 
                   ride.driver == request.user or 
                   request.user.role == 'admin'):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get latest location updates
            location_updates = LocationUpdate.objects.filter(
                ride=ride
            ).order_by('-timestamp')[:10]
            
            tracking_data = {
                'ride_id': str(ride.id),
                'status': ride.status,
                'driver': {
                    'name': f"{ride.driver.first_name} {ride.driver.last_name}" if ride.driver else None,
                    'phone': ride.driver.phone_number if ride.driver else None
                } if ride.driver else None,
                'pickup_location': {
                    'address': ride.pickup_address,
                    'latitude': float(ride.pickup_latitude) if ride.pickup_latitude else None,
                    'longitude': float(ride.pickup_longitude) if ride.pickup_longitude else None
                },
                'destination_location': {
                    'address': ride.destination_address,
                    'latitude': float(ride.destination_latitude) if ride.destination_latitude else None,
                    'longitude': float(ride.destination_longitude) if ride.destination_longitude else None
                },
                'current_location': None,
                'location_updates': LocationUpdateSerializer(location_updates, many=True).data,
                'estimated_arrival': ride.estimated_arrival_time,
                'estimated_duration': ride.estimated_duration,
                'fare': ride.fare_amount
            }
            
            # Add current location if available
            if location_updates:
                latest_update = location_updates[0]
                tracking_data['current_location'] = {
                    'latitude': float(latest_update.latitude),
                    'longitude': float(latest_update.longitude),
                    'timestamp': latest_update.timestamp,
                    'speed': latest_update.speed,
                    'heading': latest_update.heading
                }
            
            return Response(tracking_data, status=status.HTTP_200_OK)
            
        except Ride.DoesNotExist:
            return Response(
                {'error': 'Ride not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Real-time tracking error: {str(e)}")
            return Response(
                {'error': 'Tracking data unavailable'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    post=extend_schema(
        summary="Update driver location",
        description="Update current location for driver (driver only)",
        tags=['Location']
    )
)
class UpdateLocationView(APIView):
    """
    POST /api/locations/update/ - Update driver location
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Update driver location"""
        # Only drivers can update location
        if request.user.role != 'driver':
            return Response(
                {'error': 'Only drivers can update location'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = LocationUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid location data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get active ride for driver
            active_ride = Ride.objects.filter(
                driver=request.user,
                status__in=['accepted', 'driver_en_route', 'arrived', 'in_progress']
            ).first()
            
            # Create location update
            location_update = LocationUpdate.objects.create(
                user=request.user,
                ride=active_ride,
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                speed=serializer.validated_data.get('speed', 0),
                heading=serializer.validated_data.get('heading', 0),
                accuracy=serializer.validated_data.get('accuracy', 10)
            )
            
            # Broadcast location update via WebSocket
            if active_ride:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"ride_{active_ride.id}",
                    {
                        "type": "location_update",
                        "data": {
                            "ride_id": str(active_ride.id),
                            "driver_location": {
                                "latitude": float(location_update.latitude),
                                "longitude": float(location_update.longitude),
                                "timestamp": location_update.timestamp.isoformat(),
                                "speed": location_update.speed,
                                "heading": location_update.heading
                            }
                        }
                    }
                )
            
            return Response({
                'success': True,
                'message': 'Location updated successfully',
                'location_id': location_update.id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Location update error: {str(e)}")
            return Response(
                {'error': 'Failed to update location'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    get=extend_schema(
        summary="Get nearby drivers",
        description="Get list of nearby available drivers",
        tags=['Location']
    )
)
class NearbyDriversView(APIView):
    """
    GET /api/locations/nearby-drivers/ - Get nearby available drivers
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get nearby available drivers"""
        try:
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            radius = float(request.query_params.get('radius', 5.0))  # Default 5km
            
            if not latitude or not longitude:
                return Response(
                    {'error': 'Latitude and longitude are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use location service to find nearby drivers
            location_service = LocationTrackingService()
            nearby_drivers = location_service.find_nearby_drivers(
                latitude=float(latitude),
                longitude=float(longitude),
                radius=radius
            )
            
            return Response({
                'nearby_drivers': nearby_drivers,
                'search_radius': radius,
                'search_location': {
                    'latitude': float(latitude),
                    'longitude': float(longitude)
                }
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': 'Invalid coordinates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Nearby drivers error: {str(e)}")
            return Response(
                {'error': 'Failed to get nearby drivers'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    summary="Get driver location history",
    description="Get location history for a driver (admin only)",
    tags=['Location']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def driver_location_history(request, driver_id):
    """Get location history for a driver"""
    if request.user.role != 'admin':
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        driver = get_object_or_404(User, id=driver_id, role='driver')
        
        # Get recent location updates
        location_updates = LocationUpdate.objects.filter(
            user=driver
        ).order_by('-timestamp')[:50]
        
        return Response({
            'driver': {
                'id': driver.id,
                'name': f"{driver.first_name} {driver.last_name}",
                'phone': driver.phone_number
            },
            'location_history': LocationUpdateSerializer(location_updates, many=True).data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Location history error: {str(e)}")
        return Response(
            {'error': 'Failed to get location history'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get location statistics",
    description="Get location and tracking statistics",
    tags=['Location']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def location_stats(request):
    """Get location tracking statistics"""
    try:
        stats = {
            'total_location_updates': LocationUpdate.objects.count(),
            'active_tracking_sessions': LocationUpdate.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(minutes=30)
            ).values('user').distinct().count(),
            'recent_updates': LocationUpdate.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()
        }
        
        return Response(stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Location stats error: {str(e)}")
        return Response(
            {'error': 'Failed to get location statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )