"""
Location and tracking services for SafeBoda Rwanda
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
import math
from .models import Location, LocationUpdate
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class LocationTrackingService:
    """Service for handling location tracking and calculations"""
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r
    
    def find_nearby_drivers(self, latitude, longitude, radius=5.0):
        """
        Find drivers within specified radius (km) of given coordinates
        """
        try:
            # Get drivers who are available and have recent location updates
            cutoff_time = timezone.now() - timezone.timedelta(minutes=5)
            
            # Get recent location updates for available drivers
            recent_updates = LocationUpdate.objects.filter(
                timestamp__gte=cutoff_time,
                user__role='driver',
                user__is_available=True
            ).select_related('user').order_by('user', '-timestamp').distinct('user')
            
            nearby_drivers = []
            
            for update in recent_updates:
                distance = self.calculate_distance(
                    latitude, longitude,
                    update.latitude, update.longitude
                )
                
                if distance <= radius:
                    # Calculate estimated arrival time (assuming 30 km/h average speed)
                    estimated_arrival = int((distance / 30) * 60)  # minutes
                    
                    driver_data = {
                        'driver_id': update.user.id,
                        'name': f"{update.user.first_name} {update.user.last_name}",
                        'phone_number': update.user.phone_number,
                        'distance': round(distance, 2),
                        'rating': getattr(update.user, 'average_rating', 0.0),
                        'vehicle_type': getattr(update.user, 'vehicle_type', 'motorcycle'),
                        'estimated_arrival': estimated_arrival,
                        'location': {
                            'latitude': float(update.latitude),
                            'longitude': float(update.longitude),
                            'timestamp': update.timestamp.isoformat()
                        }
                    }
                    nearby_drivers.append(driver_data)
            
            # Sort by distance
            nearby_drivers.sort(key=lambda x: x['distance'])
            
            return nearby_drivers
            
        except Exception as e:
            logger.error(f"Error finding nearby drivers: {str(e)}")
            return []
    
    def calculate_route_distance(self, pickup_lat, pickup_lon, dest_lat, dest_lon):
        """
        Calculate route distance and estimated time
        In production, this would use a real routing service like Google Maps
        """
        try:
            # Simple straight-line distance calculation
            distance = self.calculate_distance(pickup_lat, pickup_lon, dest_lat, dest_lon)
            
            # Add 30% for actual road distance
            road_distance = distance * 1.3
            
            # Estimate time based on average speed in Kigali (25 km/h including traffic)
            estimated_time = (road_distance / 25) * 60  # minutes
            
            return {
                'distance_km': round(road_distance, 2),
                'estimated_time_minutes': int(estimated_time),
                'straight_line_distance': round(distance, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating route: {str(e)}")
            return {
                'distance_km': 0,
                'estimated_time_minutes': 0,
                'straight_line_distance': 0
            }
    
    def get_popular_locations(self, limit=10):
        """Get popular pickup/destination locations"""
        try:
            popular_locations = Location.objects.filter(
                is_popular=True
            ).order_by('name')[:limit]
            
            return [{
                'id': loc.id,
                'name': loc.name,
                'address': loc.address,
                'district': loc.district,
                'latitude': float(loc.latitude),
                'longitude': float(loc.longitude)
            } for loc in popular_locations]
            
        except Exception as e:
            logger.error(f"Error getting popular locations: {str(e)}")
            return []
    
    def validate_rwanda_coordinates(self, latitude, longitude):
        """
        Validate that coordinates are within Rwanda boundaries
        Rwanda bounds: approximately -2.9 to -1.0 latitude, 28.8 to 30.9 longitude
        """
        lat = float(latitude)
        lon = float(longitude)
        
        if not (-2.9 <= lat <= -1.0):
            return False
        if not (28.8 <= lon <= 30.9):
            return False
        
        return True
    
    def get_location_by_coordinates(self, latitude, longitude, radius=0.5):
        """
        Find known locations near given coordinates
        """
        try:
            nearby_locations = []
            
            for location in Location.objects.all():
                distance = self.calculate_distance(
                    latitude, longitude,
                    location.latitude, location.longitude
                )
                
                if distance <= radius:
                    nearby_locations.append({
                        'location': location,
                        'distance': distance
                    })
            
            # Sort by distance
            nearby_locations.sort(key=lambda x: x['distance'])
            
            return [item['location'] for item in nearby_locations[:5]]
            
        except Exception as e:
            logger.error(f"Error finding locations by coordinates: {str(e)}")
            return []


class GeofencingService:
    """Service for geofencing and location-based alerts"""
    
    def __init__(self):
        self.location_service = LocationTrackingService()
    
    def check_arrival_at_pickup(self, driver, pickup_lat, pickup_lon, threshold=0.1):
        """
        Check if driver has arrived at pickup location
        Threshold in kilometers
        """
        try:
            latest_update = LocationUpdate.objects.filter(
                user=driver
            ).order_by('-timestamp').first()
            
            if not latest_update:
                return False
            
            distance = self.location_service.calculate_distance(
                pickup_lat, pickup_lon,
                latest_update.latitude, latest_update.longitude
            )
            
            return distance <= threshold
            
        except Exception as e:
            logger.error(f"Error checking pickup arrival: {str(e)}")
            return False
    
    def check_arrival_at_destination(self, driver, dest_lat, dest_lon, threshold=0.1):
        """
        Check if driver has arrived at destination
        """
        return self.check_arrival_at_pickup(driver, dest_lat, dest_lon, threshold)
    
    def detect_route_deviation(self, driver, expected_route, deviation_threshold=1.0):
        """
        Detect if driver has deviated significantly from expected route
        In production, this would use proper route analysis
        """
        try:
            # Simplified implementation
            latest_update = LocationUpdate.objects.filter(
                user=driver
            ).order_by('-timestamp').first()
            
            if not latest_update or not expected_route:
                return False
            
            # Check distance from expected route points
            min_distance = float('inf')
            for point in expected_route:
                distance = self.location_service.calculate_distance(
                    latest_update.latitude, latest_update.longitude,
                    point['latitude'], point['longitude']
                )
                min_distance = min(min_distance, distance)
            
            return min_distance > deviation_threshold
            
        except Exception as e:
            logger.error(f"Error detecting route deviation: {str(e)}")
            return False


class LocationCacheService:
    """Service for caching frequently accessed location data"""
    
    @staticmethod
    def cache_popular_locations():
        """Cache popular locations for faster access"""
        # In production, this would use Redis or similar caching
        pass
    
    @staticmethod
    def cache_driver_locations():
        """Cache recent driver locations"""
        # In production, this would use Redis for real-time location data
        pass