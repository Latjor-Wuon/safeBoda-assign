"""
Location models for SafeBoda Rwanda
Handles geographic data, routing, and Rwanda-specific location services
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class Location(models.Model):
    """
    General location model for landmarks and destinations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    # Rwanda administrative divisions
    district = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    cell = models.CharField(max_length=100, blank=True)
    
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'locations'
        indexes = [
            models.Index(fields=['district', 'is_popular']),
            models.Index(fields=['is_popular', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.district}"


class LocationUpdate(models.Model):
    """
    Real-time location updates for drivers
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='location_updates')
    ride = models.ForeignKey('bookings.Ride', on_delete=models.CASCADE, null=True, blank=True, related_name='location_updates')
    
    # Location data
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    # Movement data
    speed = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # km/h
    heading = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # degrees
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, default=10)  # meters
    
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'location_updates'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['ride', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Location update for {self.user.email} at {self.timestamp}"


class RwandaLocation(models.Model):
    """
    Rwanda administrative divisions and locations
    """
    LOCATION_TYPES = (
        ('province', 'Province'),
        ('district', 'District'),
        ('sector', 'Sector'),
        ('cell', 'Cell'),
        ('village', 'Village'),
        ('landmark', 'Landmark'),
    )
    
    name = models.CharField(max_length=200)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Geographic data
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    # geometry = models.PolygonField(null=True, blank=True, geography=True)  # Disabled for basic setup
    
    # Administrative codes
    administrative_code = models.CharField(max_length=20, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rwanda_locations'
        indexes = [
            models.Index(fields=['location_type', 'parent']),
            models.Index(fields=['name']),
        ]


class PopularDestination(models.Model):
    """
    Popular destinations in Rwanda for quick booking
    """
    CATEGORY_CHOICES = (
        ('airport', 'Airport'),
        ('hospital', 'Hospital'),
        ('shopping', 'Shopping Center'),
        ('school', 'School/University'),
        ('government', 'Government Office'),
        ('transport', 'Transport Hub'),
        ('tourist', 'Tourist Attraction'),
        ('business', 'Business District'),
    )
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Location data
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    address = models.TextField()
    
    # Rwanda administrative location
    province = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    
    # Usage statistics
    booking_count = models.PositiveIntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'popular_destinations'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['booking_count']),
        ]


class DriverLocationHistory(models.Model):
    """
    Track driver location history for analytics and optimization
    """
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='location_history')
    
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    accuracy = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    speed = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    heading = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Context information
    is_online = models.BooleanField()
    is_on_ride = models.BooleanField(default=False)
    ride_id = models.UUIDField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'driver_location_history'
        indexes = [
            models.Index(fields=['driver', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]