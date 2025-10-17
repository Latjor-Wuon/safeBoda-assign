"""
Enhanced Booking Views for SafeBoda Rwanda
Complete API endpoints with integrated workflow
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes

from authentication.permissions import IsCustomerUser, IsDriverUser, IsAdminUser
from .models import Ride, RideLocation, RideRequest
from .serializers import (
    RideCreateSerializer, RideSerializer, RideListSerializer,
    RideStatusUpdateSerializer, RideCancelSerializer, RideLocationSerializer,
    RideRequestSerializer, RideRatingSerializer
)
from .integrated_service import IntegratedBookingService
import logging
import asyncio

logger = logging.getLogger(__name__)
User = get_user_model()


class AsyncAPIView(APIView):
    """Base class for async API views"""
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle async methods"""
        if asyncio.iscoroutinefunction(self.get_handler(request.method.lower())):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.async_dispatch(request, *args, **kwargs))
            finally:
                loop.close()
        return super().dispatch(request, *args, **kwargs)
    
    async def async_dispatch(self, request, *args, **kwargs):
        """Async dispatch method"""
        handler = self.get_handler(request.method.lower())
        return await handler(request, *args, **kwargs)
    
    def get_handler(self, method):
        """Get handler method for HTTP method"""
        return getattr(self, method, self.http_method_not_allowed)


@extend_schema_view(
    post=extend_schema(
        summary="Create new ride booking",
        description="Create a new ride booking with complete workflow integration including driver matching, notifications, and real-time tracking",
        tags=['Bookings'],
        request=RideCreateSerializer,
        responses={
            201: {
                'description': 'Booking created successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'success': True,
                            'ride_id': 'uuid-string',
                            'status': 'requested',
                            'estimated_fare': 3500.0,
                            'estimated_arrival': '2025-10-17T15:30:00Z',
                            'driver_matching': {
                                'status': 'searching',
                                'drivers_notified': 3
                            },
                            'tracking_enabled': True,
                            'payment_method': 'mtn_momo'
                        }
                    }
                }
            },
            400: {
                'description': 'Invalid booking data',
                'content': {
                    'application/json': {
                        'example': {
                            'success': False,
                            'error': 'You already have an active ride',
                            'error_code': 'VALIDATION_FAILED'
                        }
                    }
                }
            }
        }
    )
)
class CreateRideView(AsyncAPIView):
    """
    POST /api/bookings/create/ - Create new ride booking
    Complete integrated workflow with async processing
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomerUser]
    
    async def post(self, request):
        """Create new ride booking with integrated workflow"""
        try:
            booking_service = IntegratedBookingService()
            result = await booking_service.create_booking(request.data, request.user)
            
            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Booking creation error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Internal server error',
                'error_code': 'SYSTEM_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    get=extend_schema(
        summary="Get booking details",
        description="Get detailed information about a specific ride booking with real-time status",
        tags=['Bookings'],
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Ride booking UUID'
            )
        ],
        responses={
            200: RideSerializer,
            404: {
                'description': 'Booking not found',
                'content': {
                    'application/json': {
                        'example': {
                            'success': False,
                            'error': 'Ride not found',
                            'error_code': 'RIDE_NOT_FOUND'
                        }
                    }
                }
            }
        }
    )
)
class RideDetailView(generics.RetrieveAPIView):
    """
    GET /api/bookings/{id}/ - Get booking details
    """
    serializer_class = RideSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
    
    def get_queryset(self):
        """Filter rides based on user role"""
        user = self.request.user
        if hasattr(user, 'driver_profile'):
            # Driver can see their assigned rides
            return Ride.objects.filter(driver=user).select_related('customer')
        else:
            # Customer can see their own rides
            return Ride.objects.filter(customer=user).select_related('driver')


@extend_schema_view(
    put=extend_schema(
        summary="Update booking status",
        description="Update ride booking status with integrated workflow processing",
        tags=['Bookings'],
        request=RideStatusUpdateSerializer,
        responses={
            200: {
                'description': 'Status updated successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'success': True,
                            'ride_id': 'uuid-string',
                            'old_status': 'driver_assigned',
                            'new_status': 'driver_arrived',
                            'updated_at': '2025-10-17T15:30:00Z'
                        }
                    }
                }
            }
        }
    )
)
class UpdateRideStatusView(AsyncAPIView):
    """
    PUT /api/bookings/{id}/status/ - Update booking status
    """
    permission_classes = [permissions.IsAuthenticated]
    
    async def put(self, request, pk):
        """Update ride status with integrated workflow"""
        try:
            serializer = RideStatusUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            booking_service = IntegratedBookingService()
            result = await booking_service.update_booking_status(
                ride_id=pk,
                new_status=serializer.validated_data['status'],
                user=request.user
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Status update error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Status update failed',
                'error_code': 'UPDATE_FAILED'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    post=extend_schema(
        summary="Cancel booking",
        description="Cancel ride booking with integrated refund and notification processing",
        tags=['Bookings'],
        request=RideCancelSerializer,
        responses={
            200: {
                'description': 'Booking cancelled successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'success': True,
                            'ride_id': 'uuid-string',
                            'status': 'cancelled_by_customer',
                            'cancelled_at': '2025-10-17T15:30:00Z',
                            'reason': 'Change of plans'
                        }
                    }
                }
            }
        }
    )
)
class CancelRideView(AsyncAPIView):
    """
    POST /api/bookings/{id}/cancel/ - Cancel booking
    """
    permission_classes = [permissions.IsAuthenticated]
    
    async def post(self, request, pk):
        """Cancel ride booking with integrated workflow"""
        try:
            serializer = RideCancelSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            booking_service = IntegratedBookingService()
            result = await booking_service.cancel_booking(
                ride_id=pk,
                user=request.user,
                reason=serializer.validated_data.get('reason')
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Cancellation error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Cancellation failed',
                'error_code': 'CANCELLATION_FAILED'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    get=extend_schema(
        summary="Get active bookings",
        description="Get all active ride bookings for the authenticated user with caching",
        tags=['Bookings'],
        parameters=[
            OpenApiParameter(
                name='user_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='User type: customer or driver',
                enum=['customer', 'driver']
            )
        ],
        responses={
            200: {
                'description': 'Active bookings retrieved successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'success': True,
                            'bookings': [
                                {
                                    'ride_id': 'uuid-string',
                                    'status': 'driver_assigned',
                                    'ride_type': 'boda',
                                    'pickup_address': 'Kigali City Market',
                                    'destination_address': 'Kimisagara',
                                    'total_fare': 3500.0,
                                    'created_at': '2025-10-17T15:00:00Z',
                                    'driver': {
                                        'name': 'John Doe',
                                        'phone': '+250788123456'
                                    }
                                }
                            ],
                            'count': 1,
                            'from_cache': False
                        }
                    }
                }
            }
        }
    )
)
class ActiveRidesView(AsyncAPIView):
    """
    GET /api/bookings/active/ - Get active bookings
    """
    permission_classes = [permissions.IsAuthenticated]
    
    async def get(self, request):
        """Get active bookings with caching"""
        try:
            user_type = request.query_params.get('user_type', 'customer')
            
            # Determine user type automatically if not specified
            if user_type == 'customer' and hasattr(request.user, 'driver_profile'):
                user_type = 'driver'
            
            booking_service = IntegratedBookingService()
            result = await booking_service.get_active_bookings(
                user=request.user,
                user_type=user_type
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Active bookings retrieval error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to retrieve active bookings',
                'error_code': 'RETRIEVAL_FAILED'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Rate completed ride",
    description="Rate a completed ride and provide feedback",
    tags=['Bookings'],
    request=RideRatingSerializer,
    responses={
        200: {
            'description': 'Rating submitted successfully',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'rating': 5,
                        'feedback': 'Excellent service!',
                        'ride_id': 'uuid-string'
                    }
                }
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def rate_ride(request, pk):
    """Rate a completed ride"""
    try:
        ride = get_object_or_404(Ride, pk=pk, customer=request.user)
        
        if ride.status != 'completed':
            return Response({
                'error': 'Can only rate completed rides'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RideRatingSerializer(data=request.data)
        if serializer.is_valid():
            rating = serializer.validated_data['rating']
            feedback = serializer.validated_data.get('feedback', '')
            
            # Update ride with rating
            ride.customer_rating = rating
            ride.customer_feedback = feedback
            ride.save()
            
            # Update driver's average rating
            if ride.driver and hasattr(ride.driver, 'driver_profile'):
                driver_profile = ride.driver.driver_profile
                # Calculate new average rating
                total_ratings = Ride.objects.filter(
                    driver=ride.driver,
                    status='completed',
                    customer_rating__isnull=False
                ).count()
                
                if total_ratings > 0:
                    avg_rating = Ride.objects.filter(
                        driver=ride.driver,
                        status='completed',
                        customer_rating__isnull=False
                    ).aggregate(avg=models.Avg('customer_rating'))['avg']
                    
                    driver_profile.average_rating = avg_rating
                    driver_profile.total_ratings = total_ratings
                    driver_profile.save()
            
            return Response({
                'success': True,
                'rating': rating,
                'feedback': feedback,
                'ride_id': str(ride.id)
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Rating submission error: {str(e)}", exc_info=True)
        return Response({
            'error': 'Failed to submit rating'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Update ride location",
    description="Update real-time location during ride (driver only)",
    tags=['Bookings', 'Real-time Tracking'],
    request=RideLocationSerializer,
    responses={
        200: {
            'description': 'Location updated successfully',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'location_updated': True,
                        'timestamp': '2025-10-17T15:30:00Z'
                    }
                }
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsDriverUser])
def update_ride_location(request, pk):
    """Update ride location for real-time tracking"""
    try:
        ride = get_object_or_404(Ride, pk=pk, driver=request.user)
        
        if ride.status not in ['driver_assigned', 'driver_arrived', 'in_progress']:
            return Response({
                'error': 'Location updates only allowed for active rides'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RideLocationSerializer(data=request.data)
        if serializer.is_valid():
            # Create location update record
            RideLocation.objects.create(
                ride=ride,
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                speed=serializer.validated_data.get('speed', 0),
                heading=serializer.validated_data.get('heading', 0),
                timestamp=timezone.now()
            )
            
            # Broadcast location update via WebSocket
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            
            if channel_layer:
                import asyncio
                asyncio.run(channel_layer.group_send(
                    f"ride_{ride.id}",
                    {
                        'type': 'location_update',
                        'ride_id': str(ride.id),
                        'driver_location': {
                            'latitude': float(serializer.validated_data['latitude']),
                            'longitude': float(serializer.validated_data['longitude']),
                            'speed': serializer.validated_data.get('speed', 0),
                            'heading': serializer.validated_data.get('heading', 0),
                            'timestamp': timezone.now().isoformat()
                        }
                    }
                ))
            
            return Response({
                'success': True,
                'location_updated': True,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Location update error: {str(e)}", exc_info=True)
        return Response({
            'error': 'Failed to update location'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    get=extend_schema(
        summary="Get ride history",
        description="Get paginated ride history for the authenticated user",
        tags=['Bookings'],
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by ride status'
            )
        ],
        responses={200: RideListSerializer(many=True)}
    )
)
class RideHistoryView(generics.ListAPIView):
    """
    GET /api/bookings/history/ - Get ride history
    """
    serializer_class = RideListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get ride history based on user type"""
        user = self.request.user
        status_filter = self.request.query_params.get('status')
        
        if hasattr(user, 'driver_profile'):
            # Driver's ride history
            queryset = Ride.objects.filter(driver=user).select_related('customer')
        else:
            # Customer's ride history
            queryset = Ride.objects.filter(customer=user).select_related('driver')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')