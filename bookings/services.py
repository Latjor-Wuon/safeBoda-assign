"""
Booking services for SafeBoda Rwanda
Business logic for ride matching, fare calculation, and workflow management
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from datetime import timedelta
from authentication.models import DriverProfile
from .models import Ride, RideRequest
import math
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class RideMatchingService:
    """
    Service for matching rides with available drivers
    """
    
    def __init__(self):
        self.max_search_radius = 10  # km
        self.max_drivers_to_notify = 5
        self.request_timeout = 30  # seconds
    
    def find_available_drivers(self, ride):
        """
        Find available drivers near the pickup location
        """
        logger.info(f"Finding drivers for ride {ride.id}")
        
        # Get online drivers within search radius
        available_drivers = self._get_nearby_drivers(
            ride.pickup_latitude,
            ride.pickup_longitude,
            self.max_search_radius
        )
        
        if not available_drivers:
            self._handle_no_drivers_found(ride)
            return {
                'status': 'no_drivers',
                'message': 'No available drivers found in your area',
                'retry_in': 30
            }
        
        # Create ride requests for available drivers
        requests_created = self._create_ride_requests(ride, available_drivers)
        
        logger.info(f"Created {requests_created} ride requests for ride {ride.id}")
        
        return {
            'status': 'searching',
            'message': f'Looking for drivers... {requests_created} drivers notified',
            'drivers_notified': requests_created,
            'estimated_wait': self._estimate_wait_time(available_drivers)
        }
    
    def _get_nearby_drivers(self, latitude, longitude, radius_km):
        """
        Get available drivers within specified radius
        """
        # Calculate bounding box for efficient querying
        lat_delta = radius_km / 111.0  # Approximate km per degree latitude
        lng_delta = radius_km / (111.0 * math.cos(math.radians(float(latitude))))
        
        min_lat = float(latitude) - lat_delta
        max_lat = float(latitude) + lat_delta
        min_lng = float(longitude) - lng_delta
        max_lng = float(longitude) + lng_delta
        
        # Query for online drivers in bounding box
        available_drivers = DriverProfile.objects.filter(
            status='approved',
            is_online=True,
            user__is_active=True,
            current_latitude__gte=min_lat,
            current_latitude__lte=max_lat,
            current_longitude__gte=min_lng,
            current_longitude__lte=max_lng,
        ).exclude(
            # Exclude drivers already on a ride
            user__driver_rides__status__in=['driver_assigned', 'driver_arrived', 'in_progress']
        ).select_related('user')
        
        # Calculate exact distances and filter
        nearby_drivers = []
        for driver in available_drivers:
            distance = self._calculate_distance(
                float(latitude), float(longitude),
                float(driver.current_latitude), float(driver.current_longitude)
            )
            
            if distance <= radius_km:
                nearby_drivers.append({
                    'driver': driver,
                    'distance': distance
                })
        
        # Sort by distance and rating
        nearby_drivers.sort(key=lambda x: (x['distance'], -float(x['driver'].rating)))
        
        return nearby_drivers[:self.max_drivers_to_notify]
    
    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        """
        Calculate distance between two points using Haversine formula
        """
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _create_ride_requests(self, ride, available_drivers):
        """
        Create ride requests for available drivers
        """
        requests_created = 0
        expires_at = timezone.now() + timedelta(seconds=self.request_timeout)
        
        for driver_info in available_drivers:
            driver = driver_info['driver']
            distance = driver_info['distance']
            
            # Estimate arrival time (assume 30 km/h average speed)
            estimated_arrival = int((distance / 30) * 60)  # minutes
            
            try:
                RideRequest.objects.create(
                    ride=ride,
                    driver=driver.user,
                    driver_latitude=driver.current_latitude,
                    driver_longitude=driver.current_longitude,
                    distance_to_pickup=Decimal(str(distance)),
                    estimated_arrival_time=max(estimated_arrival, 5),  # minimum 5 minutes
                    expires_at=expires_at
                )
                requests_created += 1
                
                # Send push notification to driver (would be implemented with notification service)
                logger.info(f"Ride request sent to driver {driver.user.email} for ride {ride.id}")
                
            except Exception as e:
                logger.error(f"Failed to create ride request for driver {driver.user.email}: {str(e)}")
        
        return requests_created
    
    def _handle_no_drivers_found(self, ride):
        """
        Handle case when no drivers are found
        """
        ride.status = 'no_driver_found'
        ride.save(update_fields=['status'])
        
        logger.warning(f"No drivers found for ride {ride.id}")
    
    def _estimate_wait_time(self, available_drivers):
        """
        Estimate wait time based on available drivers
        """
        if not available_drivers:
            return 30  # Default 30 minutes
        
        # Base wait time on closest driver distance
        closest_distance = available_drivers[0]['distance']
        
        if closest_distance < 2:
            return 5  # 5 minutes
        elif closest_distance < 5:
            return 10  # 10 minutes
        else:
            return 15  # 15 minutes
    
    def accept_ride_request(self, ride_request, driver):
        """
        Handle driver accepting a ride request
        """
        if ride_request.status != 'pending':
            return False, "Request is no longer available"
        
        if ride_request.expires_at < timezone.now():
            ride_request.status = 'expired'
            ride_request.save()
            return False, "Request has expired"
        
        ride = ride_request.ride
        
        # Check if ride is still available
        if ride.status != 'requested':
            return False, "Ride is no longer available"
        
        # Accept the request
        ride_request.status = 'accepted'
        ride_request.response_time = timezone.now()
        ride_request.save()
        
        # Assign driver to ride
        ride.driver = driver
        ride.status = 'driver_assigned'
        ride.driver_assigned_at = timezone.now()
        ride.save()
        
        # Expire all other pending requests for this ride
        RideRequest.objects.filter(
            ride=ride,
            status='pending'
        ).update(status='expired')
        
        logger.info(f"Driver {driver.email} accepted ride {ride.id}")
        
        return True, "Ride request accepted successfully"


class FareCalculationService:
    """
    Service for calculating ride fares based on Rwanda pricing
    """
    
    def __init__(self):
        # Base fares in RWF
        self.base_fares = {
            'boda': Decimal('500'),
            'car': Decimal('1000'),
            'bicycle': Decimal('300'),
            'delivery': Decimal('800'),
            'express': Decimal('1200'),
        }
        
        # Per kilometer rates in RWF
        self.per_km_rates = {
            'boda': Decimal('300'),
            'car': Decimal('500'),
            'bicycle': Decimal('200'),
            'delivery': Decimal('400'),
            'express': Decimal('600'),
        }
        
        # Per minute rates in RWF (for time-based pricing)
        self.per_minute_rates = {
            'boda': Decimal('10'),
            'car': Decimal('15'),
            'bicycle': Decimal('5'),
            'delivery': Decimal('12'),
            'express': Decimal('20'),
        }
        
        # Rwanda VAT rate
        self.vat_rate = Decimal('18.0')  # 18%
        
        # Platform commission rate
        self.commission_rate = Decimal('15.0')  # 15%
    
    def calculate_fare(self, distance_km, duration_minutes, ride_type, surge_multiplier=None):
        """
        Calculate comprehensive fare breakdown
        """
        if surge_multiplier is None:
            surge_multiplier = self._calculate_surge_multiplier()
        
        base_fare = self.base_fares.get(ride_type, self.base_fares['boda'])
        per_km_rate = self.per_km_rates.get(ride_type, self.per_km_rates['boda'])
        per_minute_rate = self.per_minute_rates.get(ride_type, self.per_minute_rates['boda'])
        
        # Calculate components
        distance_charge = per_km_rate * Decimal(str(distance_km))
        time_charge = per_minute_rate * Decimal(str(duration_minutes))
        
        # Subtotal before surge and fees
        subtotal = base_fare + distance_charge + time_charge
        
        # Apply surge multiplier
        surge_charge = subtotal * (surge_multiplier - Decimal('1.0'))
        subtotal_with_surge = subtotal + surge_charge
        
        # Calculate additional charges
        night_charge = self._calculate_night_charge(subtotal_with_surge)
        toll_charge = Decimal('0')  # Would be calculated based on route
        
        # Calculate discounts (would be based on promotions, loyalty, etc.)
        promo_discount = Decimal('0')
        loyalty_discount = Decimal('0')
        
        # Calculate subtotal with all adjustments
        adjusted_subtotal = (
            subtotal_with_surge + night_charge + toll_charge -
            promo_discount - loyalty_discount
        )
        
        # Calculate VAT
        vat_amount = adjusted_subtotal * (self.vat_rate / Decimal('100'))
        
        # Final total
        total_amount = adjusted_subtotal + vat_amount
        
        return {
            'base_fare': base_fare,
            'distance_charge': distance_charge,
            'time_charge': time_charge,
            'surge_charge': surge_charge,
            'night_charge': night_charge,
            'toll_charge': toll_charge,
            'promo_discount': promo_discount,
            'loyalty_discount': loyalty_discount,
            'subtotal': adjusted_subtotal,
            'vat_amount': vat_amount,
            'vat_rate': self.vat_rate,
            'total_amount': total_amount,
            'surge_multiplier': surge_multiplier,
            'commission_amount': total_amount * (self.commission_rate / Decimal('100'))
        }
    
    def _calculate_surge_multiplier(self):
        """
        Calculate surge pricing based on demand and supply
        """
        # For now, return 1.0 (no surge)
        # In a real implementation, this would consider:
        # - Current demand vs supply ratio
        # - Time of day
        # - Weather conditions
        # - Special events
        
        current_hour = timezone.now().hour
        
        # Simple surge logic based on time
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            return Decimal('1.2')  # 20% surge during peak hours
        elif 22 <= current_hour or current_hour <= 5:
            return Decimal('1.1')  # 10% surge during night hours
        else:
            return Decimal('1.0')  # No surge
    
    def _calculate_night_charge(self, amount):
        """
        Calculate night charge (10 PM to 6 AM)
        """
        current_hour = timezone.now().hour
        
        if 22 <= current_hour or current_hour <= 6:
            return amount * Decimal('0.1')  # 10% night charge
        
        return Decimal('0')


class RideWorkflowService:
    """
    Service for managing ride workflow and status transitions
    """
    
    def __init__(self):
        self.matching_service = RideMatchingService()
        self.fare_service = FareCalculationService()
    
    def process_ride_completion(self, ride):
        """
        Process ride completion including fare calculation and payments
        """
        if ride.status != 'completed':
            return False, "Ride is not completed"
        
        # Calculate final fare if needed
        if ride.actual_distance and ride.actual_duration:
            final_fare = self.fare_service.calculate_fare(
                float(ride.actual_distance),
                ride.actual_duration,
                ride.ride_type
            )
            
            # Update ride with final calculations
            ride.total_fare = final_fare['total_amount']
            ride.save(update_fields=['total_fare'])
        
        # Update driver statistics
        if ride.driver and hasattr(ride.driver, 'driver_profile'):
            driver_profile = ride.driver.driver_profile
            driver_profile.total_rides += 1
            driver_profile.total_earnings += ride.total_fare
            driver_profile.save(update_fields=['total_rides', 'total_earnings'])
        
        # Trigger payment processing (would integrate with payment service)
        logger.info(f"Processing payment for completed ride {ride.id}: {ride.total_fare} RWF")
        
        return True, "Ride processed successfully"