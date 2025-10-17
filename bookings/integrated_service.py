"""
Integrated Booking Service for SafeBoda Rwanda
Complete ride booking workflow integration with all system components
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from channels.layers import get_channel_layer

from .models import Ride, RideRequest, RideLocation
from .services import RideMatchingService, FareCalculationService
from authentication.models import DriverProfile
from payments.services import PaymentProcessingService
from notifications.services import NotificationService
from locations.services import LocationTrackingService
from analytics.services import AnalyticsService

logger = logging.getLogger(__name__)
User = get_user_model()


@dataclass
class BookingContext:
    """Context object for booking workflow"""
    ride: Ride
    customer: User
    driver: Optional[User] = None
    payment_method: str = 'cash'
    special_requests: Optional[str] = None
    estimated_arrival: Optional[datetime] = None
    tracking_enabled: bool = True


class IntegratedBookingService:
    """
    Complete ride booking workflow integration service
    Combines user management, async location services, caching, authentication
    """
    
    def __init__(self):
        self.matching_service = RideMatchingService()
        self.fare_service = FareCalculationService()
        self.payment_service = PaymentProcessingService()
        self.notification_service = NotificationService()
        self.location_service = LocationTrackingService()
        self.analytics_service = AnalyticsService()
        self.channel_layer = get_channel_layer()
        
        # Cache keys
        self.DRIVER_CACHE_KEY = "available_drivers_{radius}_{lat}_{lng}"
        self.RIDE_CACHE_KEY = "ride_details_{ride_id}"
        self.BOOKING_CACHE_KEY = "active_bookings_{user_id}"
    
    async def create_booking(self, booking_data: Dict[str, Any], user: User) -> Dict[str, Any]:
        """
        Create a new ride booking with complete workflow integration
        """
        try:
            # Step 1: Validate user and booking data
            validation_result = await self._validate_booking_request(booking_data, user)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'error_code': 'VALIDATION_FAILED'
                }
            
            # Step 2: Calculate fare and create ride
            with transaction.atomic():
                ride = await self._create_ride_record(booking_data, user)
                
                # Step 3: Create booking context
                context = BookingContext(
                    ride=ride,
                    customer=user,
                    payment_method=booking_data.get('payment_method', 'cash'),
                    special_requests=booking_data.get('special_requests'),
                    tracking_enabled=booking_data.get('enable_tracking', True)
                )
                
                # Step 4: Cache ride details
                await self._cache_ride_details(ride)
                
                # Step 5: Start driver matching process (async)
                matching_task = asyncio.create_task(
                    self._start_driver_matching(context)
                )
                
                # Step 6: Send initial notifications
                await self._send_booking_notifications(context, 'created')
                
                # Step 7: Initialize real-time tracking
                if context.tracking_enabled:
                    await self._initialize_tracking(context)
                
                # Step 8: Record analytics
                await self._record_booking_analytics(context)
                
                # Wait for driver matching to complete
                matching_result = await matching_task
                
                return {
                    'success': True,
                    'ride_id': str(ride.id),
                    'status': ride.status,
                    'estimated_fare': float(ride.total_fare),
                    'estimated_arrival': context.estimated_arrival.isoformat() if context.estimated_arrival else None,
                    'driver_matching': matching_result,
                    'tracking_enabled': context.tracking_enabled,
                    'payment_method': context.payment_method
                }
                
        except Exception as e:
            logger.error(f"Booking creation failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Booking creation failed. Please try again.',
                'error_code': 'SYSTEM_ERROR'
            }
    
    async def update_booking_status(self, ride_id: str, new_status: str, user: User) -> Dict[str, Any]:
        """
        Update booking status with integrated workflow
        """
        try:
            # Get ride from cache or database
            ride = await self._get_ride_with_cache(ride_id)
            if not ride:
                return {
                    'success': False,
                    'error': 'Ride not found',
                    'error_code': 'RIDE_NOT_FOUND'
                }
            
            # Validate status transition
            if not self._is_valid_status_transition(ride.status, new_status):
                return {
                    'success': False,
                    'error': f'Invalid status transition from {ride.status} to {new_status}',
                    'error_code': 'INVALID_TRANSITION'
                }
            
            # Update ride status
            old_status = ride.status
            ride.status = new_status
            
            # Handle status-specific logic
            context = BookingContext(ride=ride, customer=ride.customer, driver=ride.driver)
            
            if new_status == 'driver_assigned':
                await self._handle_driver_assignment(context, user)
            elif new_status == 'driver_arrived':
                await self._handle_driver_arrival(context)
            elif new_status == 'in_progress':
                await self._handle_ride_start(context)
            elif new_status == 'completed':
                await self._handle_ride_completion(context)
            elif new_status.startswith('cancelled'):
                await self._handle_ride_cancellation(context, new_status)
            
            # Save changes
            ride.save()
            
            # Update cache
            await self._cache_ride_details(ride)
            
            # Send real-time updates
            await self._broadcast_status_update(ride, old_status, new_status)
            
            # Send notifications
            await self._send_booking_notifications(context, new_status)
            
            # Record analytics
            await self._record_status_analytics(context, old_status, new_status)
            
            return {
                'success': True,
                'ride_id': str(ride.id),
                'old_status': old_status,
                'new_status': new_status,
                'updated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Status update failed for ride {ride_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Status update failed',
                'error_code': 'UPDATE_FAILED'
            }
    
    async def cancel_booking(self, ride_id: str, user: User, reason: str = None) -> Dict[str, Any]:
        """
        Cancel booking with complete workflow integration
        """
        try:
            ride = await self._get_ride_with_cache(ride_id)
            if not ride:
                return {
                    'success': False,
                    'error': 'Ride not found',
                    'error_code': 'RIDE_NOT_FOUND'
                }
            
            # Determine cancellation type
            if user == ride.customer:
                new_status = 'cancelled_by_customer'
            elif user == ride.driver:
                new_status = 'cancelled_by_driver'
            else:
                new_status = 'cancelled_by_system'
            
            # Check if cancellation is allowed
            if not self._can_cancel_ride(ride, user):
                return {
                    'success': False,
                    'error': 'Ride cannot be cancelled at this stage',
                    'error_code': 'CANCELLATION_NOT_ALLOWED'
                }
            
            context = BookingContext(ride=ride, customer=ride.customer, driver=ride.driver)
            
            with transaction.atomic():
                # Update ride status
                old_status = ride.status
                ride.status = new_status
                ride.cancellation_reason = reason
                ride.cancelled_at = timezone.now()
                ride.save()
                
                # Handle cancellation logic
                await self._handle_ride_cancellation(context, new_status, reason)
                
                # Process refunds if needed
                if ride.payment_status == 'completed' and user == ride.customer:
                    await self._process_cancellation_refund(context)
                
                # Update driver availability
                if ride.driver:
                    await self._update_driver_availability(ride.driver, True)
                
                # Clear cache
                cache.delete(self.RIDE_CACHE_KEY.format(ride_id=ride_id))
                
                # Send notifications
                await self._send_booking_notifications(context, new_status)
                
                # Record analytics
                await self._record_cancellation_analytics(context, reason)
                
                return {
                    'success': True,
                    'ride_id': str(ride.id),
                    'status': new_status,
                    'cancelled_at': ride.cancelled_at.isoformat(),
                    'reason': reason
                }
                
        except Exception as e:
            logger.error(f"Cancellation failed for ride {ride_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Cancellation failed',
                'error_code': 'CANCELLATION_FAILED'
            }
    
    async def get_active_bookings(self, user: User, user_type: str = 'customer') -> Dict[str, Any]:
        """
        Get active bookings for user with caching
        """
        try:
            cache_key = self.BOOKING_CACHE_KEY.format(user_id=user.id)
            cached_bookings = cache.get(cache_key)
            
            if cached_bookings:
                return {
                    'success': True,
                    'bookings': cached_bookings,
                    'from_cache': True
                }
            
            # Query active bookings based on user type
            if user_type == 'customer':
                active_rides = Ride.objects.filter(
                    customer=user,
                    status__in=['requested', 'driver_assigned', 'driver_arrived', 'in_progress']
                ).select_related('driver').order_by('-created_at')
            else:  # driver
                active_rides = Ride.objects.filter(
                    driver=user,
                    status__in=['driver_assigned', 'driver_arrived', 'in_progress']
                ).select_related('customer').order_by('-created_at')
            
            # Serialize bookings
            bookings_data = []
            for ride in active_rides:
                booking_data = {
                    'ride_id': str(ride.id),
                    'status': ride.status,
                    'ride_type': ride.ride_type,
                    'pickup_address': ride.pickup_address,
                    'destination_address': ride.destination_address,
                    'total_fare': float(ride.total_fare),
                    'created_at': ride.created_at.isoformat(),
                    'estimated_duration': ride.estimated_duration
                }
                
                if user_type == 'customer' and ride.driver:
                    booking_data['driver'] = {
                        'name': f"{ride.driver.first_name} {ride.driver.last_name}",
                        'phone': ride.driver.phone_number,
                        'vehicle_details': getattr(ride.driver.driver_profile, 'vehicle_details', {})
                    }
                elif user_type == 'driver':
                    booking_data['customer'] = {
                        'name': f"{ride.customer.first_name} {ride.customer.last_name}",
                        'phone': ride.customer.phone_number
                    }
                
                bookings_data.append(booking_data)
            
            # Cache for 2 minutes
            cache.set(cache_key, bookings_data, 120)
            
            return {
                'success': True,
                'bookings': bookings_data,
                'count': len(bookings_data),
                'from_cache': False
            }
            
        except Exception as e:
            logger.error(f"Failed to get active bookings for user {user.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to retrieve bookings',
                'error_code': 'RETRIEVAL_FAILED'
            }
    
    # Private helper methods
    
    async def _validate_booking_request(self, booking_data: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Validate booking request data and user eligibility"""
        required_fields = ['pickup_latitude', 'pickup_longitude', 'pickup_address',
                          'destination_latitude', 'destination_longitude', 'destination_address']
        
        for field in required_fields:
            if field not in booking_data:
                return {'valid': False, 'error': f'Missing required field: {field}'}
        
        # Check if user has any pending rides
        pending_rides = Ride.objects.filter(
            customer=user,
            status__in=['requested', 'driver_assigned', 'driver_arrived', 'in_progress']
        ).exists()
        
        if pending_rides:
            return {'valid': False, 'error': 'You already have an active ride'}
        
        return {'valid': True}
    
    async def _create_ride_record(self, booking_data: Dict[str, Any], user: User) -> Ride:
        """Create ride record with fare calculation"""
        # Calculate fare
        fare_result = self.fare_service.calculate_fare(
            pickup_lat=booking_data['pickup_latitude'],
            pickup_lng=booking_data['pickup_longitude'],
            dest_lat=booking_data['destination_latitude'],
            dest_lng=booking_data['destination_longitude'],
            ride_type=booking_data.get('ride_type', 'boda')
        )
        
        ride = Ride.objects.create(
            customer=user,
            ride_type=booking_data.get('ride_type', 'boda'),
            pickup_latitude=booking_data['pickup_latitude'],
            pickup_longitude=booking_data['pickup_longitude'],
            pickup_address=booking_data['pickup_address'],
            destination_latitude=booking_data['destination_latitude'],
            destination_longitude=booking_data['destination_longitude'],
            destination_address=booking_data['destination_address'],
            estimated_distance=fare_result['distance'],
            estimated_duration=fare_result['duration'],
            base_fare=fare_result['base_fare'],
            distance_fare=fare_result['distance_fare'],
            total_fare=fare_result['total_fare'],
            payment_method=booking_data.get('payment_method', 'cash')
        )
        
        return ride
    
    async def _cache_ride_details(self, ride: Ride):
        """Cache ride details for quick access"""
        cache_key = self.RIDE_CACHE_KEY.format(ride_id=ride.id)
        ride_data = {
            'id': str(ride.id),
            'status': ride.status,
            'customer_id': ride.customer.id,
            'driver_id': ride.driver.id if ride.driver else None,
            'pickup_location': {
                'latitude': float(ride.pickup_latitude),
                'longitude': float(ride.pickup_longitude),
                'address': ride.pickup_address
            },
            'destination_location': {
                'latitude': float(ride.destination_latitude),
                'longitude': float(ride.destination_longitude),
                'address': ride.destination_address
            },
            'total_fare': float(ride.total_fare),
            'created_at': ride.created_at.isoformat()
        }
        cache.set(cache_key, ride_data, 3600)  # Cache for 1 hour
    
    async def _get_ride_with_cache(self, ride_id: str) -> Optional[Ride]:
        """Get ride from cache or database"""
        cache_key = self.RIDE_CACHE_KEY.format(ride_id=ride_id)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            try:
                return Ride.objects.get(id=ride_id)
            except Ride.DoesNotExist:
                cache.delete(cache_key)
                return None
        
        try:
            ride = Ride.objects.select_related('customer', 'driver').get(id=ride_id)
            await self._cache_ride_details(ride)
            return ride
        except Ride.DoesNotExist:
            return None
    
    async def _start_driver_matching(self, context: BookingContext) -> Dict[str, Any]:
        """Start asynchronous driver matching process"""
        return self.matching_service.find_available_drivers(context.ride)
    
    async def _send_booking_notifications(self, context: BookingContext, event_type: str):
        """Send notifications for booking events"""
        await self.notification_service.send_ride_notification(
            context.ride, event_type, context.customer, context.driver
        )
    
    async def _initialize_tracking(self, context: BookingContext):
        """Initialize real-time location tracking"""
        if context.tracking_enabled:
            await self.location_service.start_ride_tracking(context.ride)
    
    async def _record_booking_analytics(self, context: BookingContext):
        """Record booking analytics"""
        await self.analytics_service.record_ride_event(
            context.ride, 'booking_created', context.customer
        )
    
    async def _broadcast_status_update(self, ride: Ride, old_status: str, new_status: str):
        """Broadcast status update via WebSocket"""
        if self.channel_layer:
            await self.channel_layer.group_send(
                f"ride_{ride.id}",
                {
                    'type': 'ride_status_update',
                    'ride_id': str(ride.id),
                    'old_status': old_status,
                    'new_status': new_status,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """Validate status transition"""
        valid_transitions = {
            'requested': ['driver_assigned', 'cancelled_by_customer', 'cancelled_by_system', 'no_driver_found'],
            'driver_assigned': ['driver_arrived', 'cancelled_by_customer', 'cancelled_by_driver'],
            'driver_arrived': ['in_progress', 'cancelled_by_customer', 'cancelled_by_driver'],
            'in_progress': ['completed', 'cancelled_by_driver'],
            'completed': [],
            'cancelled_by_customer': [],
            'cancelled_by_driver': [],
            'cancelled_by_system': [],
            'no_driver_found': []
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    def _can_cancel_ride(self, ride: Ride, user: User) -> bool:
        """Check if ride can be cancelled by user"""
        if ride.status in ['completed', 'cancelled_by_customer', 'cancelled_by_driver', 'cancelled_by_system']:
            return False
        
        if user == ride.customer:
            return ride.status in ['requested', 'driver_assigned', 'driver_arrived']
        elif user == ride.driver:
            return ride.status in ['driver_assigned', 'driver_arrived']
        
        return False
    
    async def _handle_driver_assignment(self, context: BookingContext, driver: User):
        """Handle driver assignment logic"""
        context.driver = driver
        context.ride.driver = driver
        await self._update_driver_availability(driver, False)
        context.estimated_arrival = timezone.now() + timedelta(minutes=context.ride.estimated_duration)
    
    async def _handle_driver_arrival(self, context: BookingContext):
        """Handle driver arrival logic"""
        pass  # Additional logic for driver arrival
    
    async def _handle_ride_start(self, context: BookingContext):
        """Handle ride start logic"""
        context.ride.started_at = timezone.now()
    
    async def _handle_ride_completion(self, context: BookingContext):
        """Handle ride completion logic"""
        context.ride.completed_at = timezone.now()
        await self._process_ride_payment(context)
        await self._update_driver_availability(context.driver, True)
    
    async def _handle_ride_cancellation(self, context: BookingContext, status: str, reason: str = None):
        """Handle ride cancellation logic"""
        if context.driver:
            await self._update_driver_availability(context.driver, True)
    
    async def _process_ride_payment(self, context: BookingContext):
        """Process payment for completed ride"""
        if context.payment_method != 'cash':
            await self.payment_service.process_automatic_payment(context.ride)
    
    async def _process_cancellation_refund(self, context: BookingContext):
        """Process refund for cancelled ride"""
        await self.payment_service.process_refund(context.ride)
    
    async def _update_driver_availability(self, driver: User, available: bool):
        """Update driver availability status"""
        try:
            driver_profile = driver.driver_profile
            driver_profile.is_available = available
            driver_profile.save()
        except DriverProfile.DoesNotExist:
            logger.warning(f"Driver profile not found for user {driver.id}")
    
    async def _record_status_analytics(self, context: BookingContext, old_status: str, new_status: str):
        """Record status change analytics"""
        await self.analytics_service.record_status_change(
            context.ride, old_status, new_status
        )
    
    async def _record_cancellation_analytics(self, context: BookingContext, reason: str):
        """Record cancellation analytics"""
        await self.analytics_service.record_cancellation(
            context.ride, reason
        )