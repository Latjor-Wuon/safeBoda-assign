"""
Booking views for SafeBoda Rwanda
Implements all 10 required booking endpoints with complete workflow
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from authentication.permissions import IsCustomerUser, IsDriverUser, IsAdminUser
from .models import Ride, RideLocation, RideRequest
from .serializers import (
    RideCreateSerializer, RideSerializer, RideListSerializer,
    RideStatusUpdateSerializer, RideCancelSerializer, RideLocationSerializer,
    RideRequestSerializer, RideRatingSerializer
)
from .services import RideMatchingService, FareCalculationService
import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    post=extend_schema(
        summary="Create new ride booking",
        description="Create a new ride booking with pickup and destination details",
        tags=['Bookings']
    )
)
class CreateRideView(generics.CreateAPIView):
    """
    POST /api/bookings/create/ - Create new ride booking
    """
    serializer_class = RideCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomerUser]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ride = serializer.save()
        
        # Start driver matching process
        matching_service = RideMatchingService()
        matching_result = matching_service.find_available_drivers(ride)
        
        logger.info(f"Ride created: {ride.id} by {request.user.email}")
        
        response_data = {
            'ride': RideSerializer(ride).data,
            'matching_status': matching_result,
            'message': 'Ride booking created successfully'
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary="Get ride details",
        description="Retrieve detailed information about a specific ride",
        tags=['Bookings']
    )
)
class RideDetailView(generics.RetrieveAPIView):
    """
    GET /api/bookings/{id}/ - Get booking details
    """
    serializer_class = RideSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Users can only see their own rides, drivers see assigned rides, admins see all
        if user.role == 'admin':
            return Ride.objects.all()
        elif user.role == 'driver':
            return Ride.objects.filter(
                Q(driver=user) | Q(customer=user)
            )
        else:
            return Ride.objects.filter(customer=user)
    
    def retrieve(self, request, *args, **kwargs):
        ride = self.get_object()
        
        # Include additional context based on user role
        serializer = self.get_serializer(ride)
        response_data = serializer.data
        
        # Add real-time tracking data if ride is active
        if ride.is_active and ride.driver:
            recent_locations = RideLocation.objects.filter(
                ride=ride
            ).order_by('-timestamp')[:10]
            
            response_data['location_history'] = RideLocationSerializer(
                recent_locations, many=True
            ).data
        
        return Response(response_data)


@extend_schema_view(
    put=extend_schema(
        summary="Update booking status",
        description="Update ride status (driver arrival, start, completion, etc.)",
        tags=['Bookings']
    )
)
class UpdateRideStatusView(generics.UpdateAPIView):
    """
    PUT /api/bookings/{id}/status/ - Update booking status
    """
    serializer_class = RideStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'admin':
            return Ride.objects.all()
        elif user.role == 'driver':
            return Ride.objects.filter(driver=user)
        else:
            return Ride.objects.filter(customer=user)
    
    def update(self, request, *args, **kwargs):
        ride = self.get_object()
        old_status = ride.status
        
        response = super().update(request, *args, **kwargs)
        
        if response.status_code == 200:
            new_status = response.data['status']
            
            logger.info(
                f"Ride status updated: {ride.id} "
                f"from {old_status} to {new_status} by {request.user.email}"
            )
            
            # Trigger notifications based on status change
            self._send_status_notifications(ride, old_status, new_status)
        
        return response
    
    def _send_status_notifications(self, ride, old_status, new_status):
        """Send notifications for status changes"""
        # This would integrate with the notification system
        # For now, just log the events
        
        notifications = {
            'driver_assigned': f"Driver {ride.driver.full_name} has been assigned to your ride",
            'driver_arrived': "Your driver has arrived at the pickup location",
            'in_progress': "Your ride has started",
            'completed': "Your ride has been completed",
        }
        
        if new_status in notifications:
            # Send to customer
            logger.info(f"Notification to {ride.customer.email}: {notifications[new_status]}")
            
        if new_status == 'completed':
            # Send to driver
            logger.info(f"Notification to {ride.driver.email}: Ride completed successfully")


@extend_schema_view(
    post=extend_schema(
        summary="Cancel booking",
        description="Cancel a ride booking with reason",
        tags=['Bookings']
    )
)
class CancelRideView(APIView):
    """
    POST /api/bookings/{id}/cancel/ - Cancel booking
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            ride = Ride.objects.get(pk=pk)
        except Ride.DoesNotExist:
            return Response({
                'error': 'Ride not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if not (request.user == ride.customer or 
                request.user == ride.driver or 
                request.user.role == 'admin'):
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = RideCancelSerializer(
            data=request.data,
            context={'ride': ride, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Cancel the ride
        validated_data = serializer.validated_data
        old_status = ride.status
        
        # Update ride status using the status update serializer
        status_serializer = RideStatusUpdateSerializer(
            ride,
            data={
                'status': validated_data['status'],
                'reason': validated_data['reason']
            },
            context={'request': request}
        )
        status_serializer.is_valid(raise_exception=True)
        updated_ride = status_serializer.save()
        
        # Apply cancellation fee if applicable
        cancellation_fee = self._calculate_cancellation_fee(ride, request.user)
        if cancellation_fee > 0:
            updated_ride.cancellation_fee = cancellation_fee
            updated_ride.save(update_fields=['cancellation_fee'])
        
        logger.info(
            f"Ride cancelled: {ride.id} by {request.user.email} "
            f"(Fee: {cancellation_fee} RWF)"
        )
        
        return Response({
            'message': 'Ride cancelled successfully',
            'ride': RideSerializer(updated_ride).data,
            'cancellation_fee': cancellation_fee
        })
    
    def _calculate_cancellation_fee(self, ride, user):
        """Calculate cancellation fee based on Rwanda regulations"""
        from decimal import Decimal
        
        # No fee for customer cancellation within first 2 minutes
        if user == ride.customer:
            time_diff = timezone.now() - ride.created_at
            if time_diff.total_seconds() < 120:  # 2 minutes
                return Decimal('0')
            else:
                return Decimal('500')  # 500 RWF fee
        
        # Driver cancellation fee
        if user == ride.driver and ride.status in ['driver_assigned', 'driver_arrived']:
            return Decimal('1000')  # 1000 RWF penalty for driver
        
        return Decimal('0')


@extend_schema_view(
    get=extend_schema(
        summary="Get active bookings",
        description="Retrieve all active bookings for the current user",
        tags=['Bookings']
    )
)
class ActiveRidesView(generics.ListAPIView):
    """
    GET /api/bookings/active/ - Get active bookings
    """
    serializer_class = RideListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Active statuses
        active_statuses = ['requested', 'driver_assigned', 'driver_arrived', 'in_progress']
        
        if user.role == 'admin':
            return Ride.objects.filter(status__in=active_statuses)
        elif user.role == 'driver':
            return Ride.objects.filter(
                Q(driver=user, status__in=active_statuses) |
                Q(customer=user, status__in=active_statuses)
            )
        else:
            return Ride.objects.filter(
                customer=user,
                status__in=active_statuses
            )
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Add summary statistics
        total_active = queryset.count()
        status_breakdown = {}
        
        for ride in queryset:
            status_breakdown[ride.status] = status_breakdown.get(ride.status, 0) + 1
        
        return Response({
            'rides': serializer.data,
            'total_active': total_active,
            'status_breakdown': status_breakdown
        })


@extend_schema_view(
    get=extend_schema(
        summary="Get real-time tracking",
        description="Get real-time location updates for active ride",
        tags=['Bookings', 'Real-time']
    )
)
class RealTimeTrackingView(APIView):
    """
    GET /api/realtime/tracking/{booking_id}/ - Real-time location updates
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, booking_id):
        try:
            ride = Ride.objects.get(pk=booking_id)
        except Ride.DoesNotExist:
            return Response({
                'error': 'Ride not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if not (request.user == ride.customer or 
                request.user == ride.driver or 
                request.user.role == 'admin'):
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not ride.is_active:
            return Response({
                'error': 'Ride is not active'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get recent location updates
        recent_locations = RideLocation.objects.filter(
            ride=ride
        ).order_by('-timestamp')[:20]
        
        # Get driver's current location if available
        driver_location = None
        if ride.driver and hasattr(ride.driver, 'driver_profile'):
            profile = ride.driver.driver_profile
            if profile.current_latitude and profile.current_longitude:
                driver_location = {
                    'latitude': float(profile.current_latitude),
                    'longitude': float(profile.current_longitude),
                    'last_update': profile.last_location_update
                }
        
        return Response({
            'ride_id': str(ride.id),
            'status': ride.status,
            'driver_location': driver_location,
            'location_history': RideLocationSerializer(recent_locations, many=True).data,
            'pickup_location': {
                'latitude': float(ride.pickup_latitude),
                'longitude': float(ride.pickup_longitude),
                'address': ride.pickup_address
            },
            'destination_location': {
                'latitude': float(ride.destination_latitude),
                'longitude': float(ride.destination_longitude),
                'address': ride.destination_address
            }
        })


@extend_schema(
    summary="Rate completed ride",
    description="Rate and provide feedback for completed ride",
    tags=['Bookings']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def rate_ride(request, pk):
    """
    Rate completed rides
    """
    try:
        ride = Ride.objects.get(pk=pk)
    except Ride.DoesNotExist:
        return Response({
            'error': 'Ride not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if not (request.user == ride.customer or request.user == ride.driver):
        return Response({
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = RideRatingSerializer(
        ride,
        data=request.data,
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)
    updated_ride = serializer.save()
    
    logger.info(f"Ride rated: {ride.id} by {request.user.email}")
    
    return Response({
        'message': 'Rating submitted successfully',
        'ride': RideSerializer(updated_ride).data
    })


@extend_schema(
    summary="Update location during ride",
    description="Update real-time location during active ride (driver only)",
    tags=['Bookings', 'Real-time']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsDriverUser])
def update_ride_location(request, pk):
    """
    Update location during active ride
    """
    try:
        ride = Ride.objects.get(pk=pk, driver=request.user)
    except Ride.DoesNotExist:
        return Response({
            'error': 'Ride not found or not assigned to you'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not ride.is_active:
        return Response({
            'error': 'Ride is not active'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = RideLocationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Create location record
    location = RideLocation.objects.create(
        ride=ride,
        **serializer.validated_data
    )
    
    # Update driver's current location
    driver_profile = request.user.driver_profile
    driver_profile.current_latitude = serializer.validated_data['latitude']
    driver_profile.current_longitude = serializer.validated_data['longitude']
    driver_profile.last_location_update = timezone.now()
    driver_profile.save(update_fields=[
        'current_latitude', 'current_longitude', 'last_location_update'
    ])
    
    return Response({
        'message': 'Location updated successfully',
        'location': RideLocationSerializer(location).data
    })


@extend_schema(
    summary="Get ride history",
    description="Get paginated list of user's ride history",
    tags=['Bookings']
)
class RideHistoryView(generics.ListAPIView):
    """
    Get user's ride history
    """
    serializer_class = RideListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'admin':
            return Ride.objects.all().order_by('-created_at')
        elif user.role == 'driver':
            return Ride.objects.filter(
                Q(driver=user) | Q(customer=user)
            ).order_by('-created_at')
        else:
            return Ride.objects.filter(customer=user).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)