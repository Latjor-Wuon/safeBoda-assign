"""
Booking serializers for SafeBoda Rwanda
Handles ride booking, status management, and ride history
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import Ride, RideStatusHistory, RideLocation, RideRequest, RideFare
from authentication.serializers import UserProfileSerializer
from authentication.models import DriverProfile
import math

User = get_user_model()


class RideCreateSerializer(serializers.ModelSerializer):
    """
    Create new ride booking
    """
    class Meta:
        model = Ride
        fields = [
            'ride_type', 'pickup_latitude', 'pickup_longitude', 'pickup_address',
            'pickup_landmark', 'destination_latitude', 'destination_longitude',
            'destination_address', 'destination_landmark', 'payment_method',
            'customer_notes', 'special_requirements'
        ]
    
    def validate(self, data):
        """Validate ride data and calculate estimates"""
        # Calculate distance between pickup and destination
        pickup_lat = float(data['pickup_latitude'])
        pickup_lng = float(data['pickup_longitude'])
        dest_lat = float(data['destination_latitude'])
        dest_lng = float(data['destination_longitude'])
        
        distance = self.calculate_distance(pickup_lat, pickup_lng, dest_lat, dest_lng)
        
        if distance < 0.1:  # Minimum 100 meters
            raise serializers.ValidationError(
                "Pickup and destination must be at least 100 meters apart"
            )
        
        if distance > 500:  # Maximum 500 km
            raise serializers.ValidationError(
                "Distance cannot exceed 500 kilometers"
            )
        
        # Add calculated fields
        data['estimated_distance'] = Decimal(str(distance))
        data['estimated_duration'] = self.calculate_duration(distance, data['ride_type'])
        
        # Calculate fare
        fare_details = self.calculate_fare(distance, data['ride_type'])
        data.update(fare_details)
        
        return data
    
    def calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two points using Haversine formula"""
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
    
    def calculate_duration(self, distance, ride_type):
        """Calculate estimated duration based on distance and ride type"""
        # Average speeds in km/h
        speed_map = {
            'boda': 30,  # Motorcycle
            'car': 25,   # Car in city traffic
            'bicycle': 15,
            'delivery': 25,
            'express': 35,
        }
        
        speed = speed_map.get(ride_type, 25)
        duration_hours = distance / speed
        
        # Convert to minutes and add buffer time
        duration_minutes = int(duration_hours * 60) + 5  # 5 min buffer
        
        return max(duration_minutes, 10)  # Minimum 10 minutes
    
    def calculate_fare(self, distance, ride_type):
        """Calculate fare based on Rwanda pricing structure"""
        # Base fare in RWF
        base_fares = {
            'boda': Decimal('500'),
            'car': Decimal('1000'),
            'bicycle': Decimal('300'),
            'delivery': Decimal('800'),
            'express': Decimal('1200'),
        }
        
        # Per kilometer rate
        per_km_rates = {
            'boda': Decimal('300'),
            'car': Decimal('500'),
            'bicycle': Decimal('200'),
            'delivery': Decimal('400'),
            'express': Decimal('600'),
        }
        
        base_fare = base_fares.get(ride_type, Decimal('500'))
        per_km_rate = per_km_rates.get(ride_type, Decimal('300'))
        
        distance_fare = per_km_rate * Decimal(str(distance))
        time_fare = Decimal('0')  # No time-based fare for now
        surge_multiplier = Decimal('1.0')  # No surge for now
        
        total_fare = (base_fare + distance_fare + time_fare) * surge_multiplier
        
        return {
            'base_fare': base_fare,
            'distance_fare': distance_fare,
            'time_fare': time_fare,
            'surge_multiplier': surge_multiplier,
            'total_fare': total_fare,
        }
    
    def create(self, validated_data):
        """Create ride with customer"""
        validated_data['customer'] = self.context['request'].user
        validated_data['status'] = 'requested'
        
        ride = Ride.objects.create(**validated_data)
        
        # Create initial status history
        RideStatusHistory.objects.create(
            ride=ride,
            to_status='requested',
            changed_by=ride.customer,
            reason='Ride requested by customer'
        )
        
        return ride


class RideSerializer(serializers.ModelSerializer):
    """
    Full ride details serializer
    """
    customer = UserProfileSerializer(read_only=True)
    driver = UserProfileSerializer(read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Ride
        fields = '__all__'


class RideListSerializer(serializers.ModelSerializer):
    """
    Simplified ride list serializer
    """
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Ride
        fields = [
            'id', 'status', 'ride_type', 'customer_name', 'driver_name',
            'pickup_address', 'destination_address', 'total_fare',
            'payment_method', 'payment_status', 'estimated_duration',
            'duration_minutes', 'is_active', 'created_at', 'updated_at'
        ]


class RideStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Update ride status
    """
    reason = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Ride
        fields = ['status', 'reason']
    
    def validate_status(self, value):
        """Validate status transition"""
        current_status = self.instance.status
        user = self.context['request'].user
        
        # Define valid transitions
        valid_transitions = {
            'requested': ['driver_assigned', 'cancelled_by_customer', 'cancelled_by_system', 'no_driver_found'],
            'driver_assigned': ['driver_arrived', 'cancelled_by_driver', 'cancelled_by_customer'],
            'driver_arrived': ['in_progress', 'cancelled_by_driver', 'cancelled_by_customer'],
            'in_progress': ['completed', 'cancelled_by_driver', 'cancelled_by_customer'],
            'completed': [],  # Final status
            'cancelled_by_customer': [],  # Final status
            'cancelled_by_driver': [],  # Final status
            'cancelled_by_system': [],  # Final status
            'no_driver_found': ['requested'],  # Can retry
        }
        
        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot transition from {current_status} to {value}"
            )
        
        # Validate user permissions for status change
        if user.role == 'customer' and value not in ['cancelled_by_customer']:
            if current_status == 'requested' and value != 'cancelled_by_customer':
                raise serializers.ValidationError(
                    "Customers can only cancel their rides"
                )
        
        elif user.role == 'driver' and value not in [
            'driver_assigned', 'driver_arrived', 'in_progress', 'completed', 'cancelled_by_driver'
        ]:
            raise serializers.ValidationError(
                "Invalid status change for driver"
            )
        
        return value
    
    def update(self, instance, validated_data):
        """Update status and create history record"""
        old_status = instance.status
        new_status = validated_data['status']
        reason = validated_data.get('reason', '')
        user = self.context['request'].user
        
        # Update ride status
        instance.status = new_status
        
        # Update timestamps based on status
        now = timezone.now()
        if new_status == 'driver_assigned':
            instance.driver_assigned_at = now
        elif new_status == 'driver_arrived':
            instance.driver_arrived_at = now
        elif new_status == 'in_progress':
            instance.ride_started_at = now
        elif new_status == 'completed':
            instance.ride_ended_at = now
        elif new_status.startswith('cancelled'):
            instance.cancelled_at = now
        
        instance.save()
        
        # Create status history
        RideStatusHistory.objects.create(
            ride=instance,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            reason=reason
        )
        
        return instance


class RideCancelSerializer(serializers.Serializer):
    """
    Cancel ride with reason
    """
    reason = serializers.CharField(max_length=500)
    
    def validate(self, data):
        """Validate cancellation"""
        ride = self.context['ride']
        user = self.context['request'].user
        
        if ride.status not in ['requested', 'driver_assigned', 'driver_arrived']:
            raise serializers.ValidationError(
                "Cannot cancel ride in current status"
            )
        
        # Check if user can cancel
        if user == ride.customer:
            data['status'] = 'cancelled_by_customer'
        elif user == ride.driver:
            data['status'] = 'cancelled_by_driver'
        elif user.role == 'admin':
            data['status'] = 'cancelled_by_system'
        else:
            raise serializers.ValidationError(
                "You don't have permission to cancel this ride"
            )
        
        return data


class RideLocationSerializer(serializers.ModelSerializer):
    """
    Real-time location updates during rides
    """
    class Meta:
        model = RideLocation
        fields = [
            'latitude', 'longitude', 'accuracy', 'speed', 'heading', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class RideRequestSerializer(serializers.ModelSerializer):
    """
    Driver response to ride requests
    """
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    
    class Meta:
        model = RideRequest
        fields = [
            'id', 'driver', 'driver_name', 'driver_latitude', 'driver_longitude',
            'distance_to_pickup', 'estimated_arrival_time', 'status',
            'response_time', 'created_at', 'expires_at'
        ]
        read_only_fields = ['driver', 'response_time', 'created_at']


class RideFareSerializer(serializers.ModelSerializer):
    """
    Detailed fare breakdown
    """
    class Meta:
        model = RideFare
        fields = '__all__'
        read_only_fields = ['ride']


class RideRatingSerializer(serializers.ModelSerializer):
    """
    Rate completed rides
    """
    class Meta:
        model = Ride
        fields = ['customer_rating', 'driver_rating', 'customer_feedback', 'driver_feedback']
    
    def validate(self, data):
        """Validate rating permissions"""
        ride = self.instance
        user = self.context['request'].user
        
        if ride.status != 'completed':
            raise serializers.ValidationError("Can only rate completed rides")
        
        # Customers can only rate drivers
        if user == ride.customer:
            if 'customer_rating' in data or 'customer_feedback' in data:
                raise serializers.ValidationError(
                    "Customers can only provide driver_rating and driver_feedback"
                )
        
        # Drivers can only rate customers
        elif user == ride.driver:
            if 'driver_rating' in data or 'driver_feedback' in data:
                raise serializers.ValidationError(
                    "Drivers can only provide customer_rating and customer_feedback"
                )
        
        return data