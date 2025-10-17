"""
Enhanced Real-time Tracking API for SafeBoda Rwanda
WebSocket-based location tracking with caching and integration
"""
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .models import Location, LocationUpdate
from bookings.models import Ride, RideLocation
from authentication.models import DriverProfile
from .serializers import LocationSerializer, LocationUpdateSerializer, RealTimeTrackingSerializer
from .services import LocationTrackingService

logger = logging.getLogger(__name__)
User = get_user_model()


class RealTimeTrackingAPIView(APIView):
    """
    Enhanced real-time tracking API with WebSocket integration
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.location_service = LocationTrackingService()
        self.channel_layer = get_channel_layer()
        
        # Cache configuration
        self.TRACKING_CACHE_TTL = 30  # 30 seconds
        self.LOCATION_CACHE_TTL = 60  # 1 minute
        self.DRIVER_LOCATION_CACHE_KEY = "driver_location_{driver_id}"
        self.RIDE_TRACKING_CACHE_KEY = "ride_tracking_{ride_id}"


@extend_schema(
    summary="Get real-time tracking for booking",
    description="Get real-time location updates and tracking information for a specific booking with WebSocket support",
    tags=['Real-time Tracking'],
    parameters=[
        OpenApiParameter(
            name='booking_id',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Booking/Ride UUID'
        ),
        OpenApiParameter(
            name='include_history',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Include location history'
        ),
        OpenApiParameter(
            name='history_minutes',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Minutes of history to include (default: 10)'
        )
    ],
    responses={
        200: {
            'description': 'Real-time tracking data',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'ride_id': 'uuid-string',
                        'status': 'in_progress',
                        'tracking_active': True,
                        'current_location': {
                            'latitude': -1.9441,
                            'longitude': 30.0619,
                            'speed': 25.5,
                            'heading': 180,
                            'timestamp': '2025-10-17T15:30:00Z'
                        },
                        'driver_info': {
                            'name': 'John Doe',
                            'phone': '+250788123456',
                            'vehicle_plate': 'RAD 123A'
                        },
                        'route_info': {
                            'distance_remaining': 2.5,
                            'estimated_arrival': '2025-10-17T15:45:00Z',
                            'progress_percentage': 65
                        },
                        'websocket_url': 'wss://api.safeboda.rw/ws/tracking/uuid-string/',
                        'location_history': [],
                        'from_cache': False
                    }
                }
            }
        },
        403: {
            'description': 'Permission denied',
            'content': {
                'application/json': {
                    'example': {
                        'success': False,
                        'error': 'Permission denied',
                        'error_code': 'PERMISSION_DENIED'
                    }
                }
            }
        },
        404: {
            'description': 'Booking not found',
            'content': {
                'application/json': {
                    'example': {
                        'success': False,
                        'error': 'Booking not found',
                        'error_code': 'BOOKING_NOT_FOUND'
                    }
                }
            }
        }
    }
)
class RealTimeTrackingView(RealTimeTrackingAPIView):
    """
    GET /api/realtime/tracking/{booking_id}/ - Real-time location updates
    """
    
    def get(self, request, booking_id):
        """Get comprehensive real-time tracking data"""
        try:
            # Check cache first
            cache_key = self.RIDE_TRACKING_CACHE_KEY.format(ride_id=booking_id)
            cached_data = cache.get(cache_key)
            
            if cached_data and not request.query_params.get('force_refresh'):
                cached_data['from_cache'] = True
                return Response(cached_data, status=status.HTTP_200_OK)
            
            # Get ride from database
            ride = get_object_or_404(Ride, id=booking_id)
            
            # Check permissions
            if not self._has_tracking_permission(ride, request.user):
                return Response({
                    'success': False,
                    'error': 'Permission denied',
                    'error_code': 'PERMISSION_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Build tracking response
            tracking_data = self._build_tracking_response(ride, request)
            
            # Cache the response
            cache.set(cache_key, tracking_data, self.TRACKING_CACHE_TTL)
            
            tracking_data['from_cache'] = False
            return Response(tracking_data, status=status.HTTP_200_OK)
            
        except Ride.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Booking not found',
                'error_code': 'BOOKING_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Real-time tracking error for booking {booking_id}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to retrieve tracking data',
                'error_code': 'TRACKING_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _has_tracking_permission(self, ride: Ride, user: User) -> bool:
        """Check if user has permission to view tracking data"""
        return (
            ride.customer == user or 
            ride.driver == user or 
            getattr(user, 'role', 'customer') == 'admin'
        )
    
    def _build_tracking_response(self, ride: Ride, request) -> Dict[str, Any]:
        """Build comprehensive tracking response"""
        # Get latest location data
        current_location = self._get_current_location(ride)
        
        # Get driver information
        driver_info = self._get_driver_info(ride.driver) if ride.driver else None
        
        # Calculate route information
        route_info = self._calculate_route_info(ride, current_location)
        
        # Get location history if requested
        location_history = []
        if request.query_params.get('include_history', 'false').lower() == 'true':
            history_minutes = int(request.query_params.get('history_minutes', 10))
            location_history = self._get_location_history(ride, history_minutes)
        
        # Build WebSocket URL
        websocket_url = f"wss://{request.get_host()}/ws/tracking/{ride.id}/"
        
        return {
            'success': True,
            'ride_id': str(ride.id),
            'status': ride.status,
            'tracking_active': ride.status in ['driver_assigned', 'driver_arrived', 'in_progress'],
            'current_location': current_location,
            'driver_info': driver_info,
            'route_info': route_info,
            'websocket_url': websocket_url,
            'location_history': location_history,
            'updated_at': timezone.now().isoformat()
        }
    
    def _get_current_location(self, ride: Ride) -> Optional[Dict[str, Any]]:
        """Get current driver location"""
        if not ride.driver:
            return None
        
        # Check cache first
        cache_key = self.DRIVER_LOCATION_CACHE_KEY.format(driver_id=ride.driver.id)
        cached_location = cache.get(cache_key)
        
        if cached_location:
            return cached_location
        
        # Get latest location from database
        latest_location = RideLocation.objects.filter(
            ride=ride
        ).order_by('-timestamp').first()
        
        if latest_location:
            location_data = {
                'latitude': float(latest_location.latitude),
                'longitude': float(latest_location.longitude),
                'speed': latest_location.speed,
                'heading': latest_location.heading,
                'timestamp': latest_location.timestamp.isoformat()
            }
            
            # Cache for quick access
            cache.set(cache_key, location_data, self.LOCATION_CACHE_TTL)
            return location_data
        
        # Fallback to driver profile location
        if hasattr(ride.driver, 'driver_profile'):
            profile = ride.driver.driver_profile
            if profile.current_latitude and profile.current_longitude:
                return {
                    'latitude': float(profile.current_latitude),
                    'longitude': float(profile.current_longitude),
                    'speed': 0,
                    'heading': 0,
                    'timestamp': profile.location_updated_at.isoformat() if profile.location_updated_at else None
                }
        
        return None
    
    def _get_driver_info(self, driver: User) -> Optional[Dict[str, Any]]:
        """Get driver information for tracking"""
        if not driver:
            return None
        
        driver_info = {
            'name': f"{driver.first_name} {driver.last_name}".strip(),
            'phone': driver.phone_number
        }
        
        # Add vehicle information if available
        if hasattr(driver, 'driver_profile'):
            profile = driver.driver_profile
            driver_info.update({
                'vehicle_plate': profile.vehicle_plate_number,
                'vehicle_type': profile.vehicle_type,
                'vehicle_model': profile.vehicle_model,
                'rating': float(profile.average_rating) if profile.average_rating else 0.0
            })
        
        return driver_info
    
    def _calculate_route_info(self, ride: Ride, current_location: Optional[Dict]) -> Dict[str, Any]:
        """Calculate route progress and estimated arrival"""
        route_info = {
            'distance_remaining': 0.0,
            'estimated_arrival': None,
            'progress_percentage': 0
        }
        
        if not current_location:
            return route_info
        
        try:
            # Calculate distance remaining using the location service
            distance_remaining = self.location_service.calculate_distance(
                current_location['latitude'],
                current_location['longitude'],
                float(ride.destination_latitude),
                float(ride.destination_longitude)
            )
            
            # Calculate progress percentage
            total_distance = float(ride.estimated_distance)
            if total_distance > 0:
                progress = max(0, min(100, ((total_distance - distance_remaining) / total_distance) * 100))
                route_info['progress_percentage'] = round(progress, 1)
            
            route_info['distance_remaining'] = round(distance_remaining, 2)
            
            # Estimate arrival time based on current speed and distance
            current_speed = current_location.get('speed', 0)
            if current_speed > 0 and distance_remaining > 0:
                # Convert speed from km/h to m/s, then calculate time
                speed_ms = current_speed * 1000 / 3600
                estimated_seconds = (distance_remaining * 1000) / speed_ms
                estimated_arrival = timezone.now() + timedelta(seconds=estimated_seconds)
                route_info['estimated_arrival'] = estimated_arrival.isoformat()
            
        except Exception as e:
            logger.warning(f"Route calculation error for ride {ride.id}: {str(e)}")
        
        return route_info
    
    def _get_location_history(self, ride: Ride, minutes: int) -> List[Dict[str, Any]]:
        """Get location history for the specified time period"""
        since_time = timezone.now() - timedelta(minutes=minutes)
        
        history = RideLocation.objects.filter(
            ride=ride,
            timestamp__gte=since_time
        ).order_by('timestamp').values(
            'latitude', 'longitude', 'speed', 'heading', 'timestamp'
        )
        
        return [
            {
                'latitude': float(loc['latitude']),
                'longitude': float(loc['longitude']),
                'speed': loc['speed'],
                'heading': loc['heading'],
                'timestamp': loc['timestamp'].isoformat()
            }
            for loc in history
        ]


@extend_schema(
    summary="Update driver location",
    description="Update driver's current location for real-time tracking (driver only)",
    tags=['Real-time Tracking'],
    request=LocationUpdateSerializer,
    responses={
        200: {
            'description': 'Location updated successfully',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'location_updated': True,
                        'broadcast_sent': True,
                        'active_rides_count': 1,
                        'timestamp': '2025-10-17T15:30:00Z'
                    }
                }
            }
        }
    }
)
class UpdateLocationView(RealTimeTrackingAPIView):
    """
    POST /api/realtime/location/ - Update driver location
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Update driver's current location"""
        try:
            # Validate that user is a driver
            if not hasattr(request.user, 'driver_profile'):
                return Response({
                    'success': False,
                    'error': 'Only drivers can update location',
                    'error_code': 'PERMISSION_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = LocationUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Invalid location data',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            location_data = serializer.validated_data
            driver = request.user
            
            # Update driver profile location
            driver_profile = driver.driver_profile
            driver_profile.current_latitude = location_data['latitude']
            driver_profile.current_longitude = location_data['longitude']
            driver_profile.location_updated_at = timezone.now()
            driver_profile.save()
            
            # Update location cache
            cache_key = self.DRIVER_LOCATION_CACHE_KEY.format(driver_id=driver.id)
            cached_location = {
                'latitude': float(location_data['latitude']),
                'longitude': float(location_data['longitude']),
                'speed': location_data.get('speed', 0),
                'heading': location_data.get('heading', 0),
                'timestamp': timezone.now().isoformat()
            }
            cache.set(cache_key, cached_location, self.LOCATION_CACHE_TTL)
            
            # Find active rides for this driver
            active_rides = Ride.objects.filter(
                driver=driver,
                status__in=['driver_assigned', 'driver_arrived', 'in_progress']
            )
            
            broadcast_count = 0
            # Update location for each active ride and broadcast
            for ride in active_rides:
                # Create ride location record
                RideLocation.objects.create(
                    ride=ride,
                    latitude=location_data['latitude'],
                    longitude=location_data['longitude'],
                    speed=location_data.get('speed', 0),
                    heading=location_data.get('heading', 0),
                    timestamp=timezone.now()
                )
                
                # Broadcast via WebSocket
                if self.channel_layer:
                    async_to_sync(self.channel_layer.group_send)(
                        f"ride_{ride.id}",
                        {
                            'type': 'location_update',
                            'ride_id': str(ride.id),
                            'driver_location': cached_location
                        }
                    )
                    broadcast_count += 1
                
                # Clear ride tracking cache
                ride_cache_key = self.RIDE_TRACKING_CACHE_KEY.format(ride_id=ride.id)
                cache.delete(ride_cache_key)
            
            return Response({
                'success': True,
                'location_updated': True,
                'broadcast_sent': broadcast_count > 0,
                'active_rides_count': len(active_rides),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Location update error for driver {request.user.id}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to update location',
                'error_code': 'UPDATE_FAILED'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get nearby drivers",
    description="Get available drivers near a specified location with real-time data",
    tags=['Real-time Tracking'],
    parameters=[
        OpenApiParameter(
            name='latitude',
            type=OpenApiTypes.NUMBER,
            location=OpenApiParameter.QUERY,
            description='Latitude coordinate'
        ),
        OpenApiParameter(
            name='longitude',
            type=OpenApiTypes.NUMBER,
            location=OpenApiParameter.QUERY,
            description='Longitude coordinate'
        ),
        OpenApiParameter(
            name='radius',
            type=OpenApiTypes.NUMBER,
            location=OpenApiParameter.QUERY,
            description='Search radius in kilometers (default: 5)'
        ),
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Maximum number of drivers to return (default: 10)'
        )
    ],
    responses={
        200: {
            'description': 'Nearby drivers found',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'drivers': [
                            {
                                'driver_id': 'uuid-string',
                                'name': 'John Doe',
                                'distance_km': 1.2,
                                'estimated_arrival_minutes': 3,
                                'rating': 4.8,
                                'vehicle_type': 'motorcycle',
                                'current_location': {
                                    'latitude': -1.9441,
                                    'longitude': 30.0619
                                },
                                'last_updated': '2025-10-17T15:30:00Z'
                            }
                        ],
                        'count': 1,
                        'search_radius': 5.0,
                        'from_cache': False
                    }
                }
            }
        }
    }
)
class NearbyDriversView(RealTimeTrackingAPIView):
    """
    GET /api/realtime/nearby-drivers/ - Get nearby available drivers
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get nearby available drivers with real-time locations"""
        try:
            # Validate required parameters
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            
            if not latitude or not longitude:
                return Response({
                    'success': False,
                    'error': 'Latitude and longitude are required',
                    'error_code': 'MISSING_COORDINATES'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                latitude = float(latitude)
                longitude = float(longitude)
                radius = float(request.query_params.get('radius', 5.0))
                limit = int(request.query_params.get('limit', 10))
            except ValueError:
                return Response({
                    'success': False,
                    'error': 'Invalid coordinate or radius values',
                    'error_code': 'INVALID_PARAMETERS'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check cache first
            cache_key = f"nearby_drivers_{latitude}_{longitude}_{radius}_{limit}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                cached_data['from_cache'] = True
                return Response(cached_data, status=status.HTTP_200_OK)
            
            # Find nearby drivers
            nearby_drivers = self._find_nearby_drivers(latitude, longitude, radius, limit)
            
            response_data = {
                'success': True,
                'drivers': nearby_drivers,
                'count': len(nearby_drivers),
                'search_radius': radius,
                'search_location': {
                    'latitude': latitude,
                    'longitude': longitude
                },
                'from_cache': False
            }
            
            # Cache for 1 minute
            cache.set(cache_key, response_data, 60)
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Nearby drivers search error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to find nearby drivers',
                'error_code': 'SEARCH_FAILED'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _find_nearby_drivers(self, latitude: float, longitude: float, radius: float, limit: int) -> List[Dict[str, Any]]:
        """Find available drivers within specified radius"""
        import math
        
        # Calculate bounding box for efficient querying
        lat_delta = radius / 111.0  # Approximate km per degree latitude
        lng_delta = radius / (111.0 * math.cos(math.radians(latitude)))
        
        min_lat = latitude - lat_delta
        max_lat = latitude + lat_delta
        min_lng = longitude - lng_delta
        max_lng = longitude + lng_delta
        
        # Query for online drivers in bounding box
        available_drivers = DriverProfile.objects.filter(
            status='approved',
            is_online=True,
            is_available=True,
            user__is_active=True,
            current_latitude__gte=min_lat,
            current_latitude__lte=max_lat,
            current_longitude__gte=min_lng,
            current_longitude__lte=max_lng,
            location_updated_at__gte=timezone.now() - timedelta(minutes=5)  # Recent location
        ).exclude(
            # Exclude drivers already on a ride
            user__driver_rides__status__in=['driver_assigned', 'driver_arrived', 'in_progress']
        ).select_related('user')[:limit * 2]  # Get more than needed for filtering
        
        # Calculate exact distances and filter
        nearby_drivers = []
        for driver in available_drivers:
            if not driver.current_latitude or not driver.current_longitude:
                continue
                
            distance = self.location_service.calculate_distance(
                latitude, longitude,
                float(driver.current_latitude), float(driver.current_longitude)
            )
            
            if distance <= radius:
                # Estimate arrival time (assuming average speed of 25 km/h)
                estimated_minutes = max(1, int((distance / 25) * 60))
                
                driver_data = {
                    'driver_id': str(driver.user.id),
                    'name': f"{driver.user.first_name} {driver.user.last_name}".strip(),
                    'distance_km': round(distance, 2),
                    'estimated_arrival_minutes': estimated_minutes,
                    'rating': float(driver.average_rating) if driver.average_rating else 0.0,
                    'vehicle_type': driver.vehicle_type,
                    'vehicle_plate': driver.vehicle_plate_number,
                    'current_location': {
                        'latitude': float(driver.current_latitude),
                        'longitude': float(driver.current_longitude)
                    },
                    'last_updated': driver.location_updated_at.isoformat() if driver.location_updated_at else None
                }
                
                nearby_drivers.append(driver_data)
        
        # Sort by distance and limit results
        nearby_drivers.sort(key=lambda x: x['distance_km'])
        return nearby_drivers[:limit]


@extend_schema(
    summary="Start ride tracking",
    description="Initialize real-time tracking for a ride (system internal)",
    tags=['Real-time Tracking'],
    responses={
        200: {
            'description': 'Tracking started successfully',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'tracking_started': True,
                        'websocket_room': 'ride_uuid-string',
                        'tracking_config': {
                            'update_interval': 10,
                            'max_history_points': 100
                        }
                    }
                }
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_ride_tracking(request, booking_id):
    """Start real-time tracking for a ride"""
    try:
        ride = get_object_or_404(Ride, id=booking_id)
        
        # Check permissions
        if not (ride.driver == request.user or getattr(request.user, 'role', 'customer') == 'admin'):
            return Response({
                'success': False,
                'error': 'Permission denied',
                'error_code': 'PERMISSION_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Initialize tracking
        tracking_service = LocationTrackingService()
        tracking_result = tracking_service.start_ride_tracking(ride)
        
        # Create WebSocket room for this ride
        if request.channel_layer:
            async_to_sync(request.channel_layer.group_add)(
                f"ride_{ride.id}",
                f"tracking_{request.user.id}"
            )
        
        return Response({
            'success': True,
            'tracking_started': True,
            'websocket_room': f"ride_{ride.id}",
            'tracking_config': {
                'update_interval': 10,  # seconds
                'max_history_points': 100
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to start tracking for ride {booking_id}: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to start tracking',
            'error_code': 'TRACKING_START_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)