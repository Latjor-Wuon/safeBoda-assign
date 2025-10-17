"""
Location serializers for SafeBoda Rwanda - Enhanced Real-time Tracking
"""
from rest_framework import serializers
from .models import Location, LocationUpdate
from bookings.models import RideLocation
from decimal import Decimal


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for locations"""
    
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'address', 'latitude', 'longitude',
            'district', 'sector', 'cell', 'is_popular',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LocationUpdateSerializer(serializers.Serializer):
    """Enhanced serializer for real-time location updates"""
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    speed = serializers.FloatField(min_value=0, max_value=200, default=0)  # km/h
    heading = serializers.FloatField(min_value=0, max_value=360, default=0)  # degrees
    accuracy = serializers.FloatField(min_value=0, default=10)  # meters
    timestamp = serializers.DateTimeField(required=False)
    
    def validate_latitude(self, value):
        """Validate latitude is within Rwanda bounds"""
        if not (-3.0 <= float(value) <= -1.0):
            raise serializers.ValidationError("Latitude must be within Rwanda bounds (-3.0 to -1.0)")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude is within Rwanda bounds"""
        if not (28.5 <= float(value) <= 31.0):
            raise serializers.ValidationError("Longitude must be within Rwanda bounds (28.5 to 31.0)")
        return value


class RealTimeTrackingSerializer(serializers.Serializer):
    """Serializer for real-time tracking response"""
    success = serializers.BooleanField()
    ride_id = serializers.UUIDField()
    status = serializers.CharField()
    tracking_active = serializers.BooleanField()
    current_location = serializers.DictField(required=False, allow_null=True)
    driver_info = serializers.DictField(required=False, allow_null=True)
    route_info = serializers.DictField()
    websocket_url = serializers.URLField()
    location_history = serializers.ListField(child=serializers.DictField(), default=list)
    updated_at = serializers.DateTimeField()
    from_cache = serializers.BooleanField(default=False)


class RideLocationSerializer(serializers.ModelSerializer):
    """Serializer for ride location tracking"""
    
    class Meta:
        model = RideLocation
        fields = [
            'id', 'ride', 'latitude', 'longitude', 
            'speed', 'heading', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class NearbyDriverSerializer(serializers.Serializer):
    """Serializer for nearby driver information"""
    driver_id = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    distance_km = serializers.FloatField()
    estimated_arrival_minutes = serializers.IntegerField()
    rating = serializers.FloatField(min_value=0, max_value=5)
    vehicle_type = serializers.CharField(max_length=50)
    vehicle_plate = serializers.CharField(max_length=20, required=False)
    current_location = serializers.DictField()
    last_updated = serializers.DateTimeField(required=False, allow_null=True)


class TrackingConfigSerializer(serializers.Serializer):
    """Serializer for tracking configuration"""
    update_interval = serializers.IntegerField(min_value=5, max_value=60, default=10)
    max_history_points = serializers.IntegerField(min_value=10, max_value=500, default=100)
    enable_notifications = serializers.BooleanField(default=True)
    tracking_accuracy = serializers.ChoiceField(
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium'
    )
    
    class Meta:
        model = Location
        read_only_fields = ['id', 'timestamp']


class LocationTrackingSerializer(serializers.Serializer):
    """Serializer for location tracking requests"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    speed = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    heading = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    accuracy = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=10)


class NearbyDriverSerializer(serializers.Serializer):
    """Serializer for nearby driver information"""
    driver_id = serializers.UUIDField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    distance = serializers.DecimalField(max_digits=5, decimal_places=2)
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)
    vehicle_type = serializers.CharField(required=False)
    estimated_arrival = serializers.IntegerField()  # in minutes
    location = serializers.DictField()