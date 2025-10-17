"""
Booking models for SafeBoda Rwanda
Handles ride booking, status management, and ride history
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

User = get_user_model()


class Ride(models.Model):
    """
    Core ride booking model with Rwanda-specific features
    """
    STATUS_CHOICES = (
        ('requested', 'Ride Requested'),
        ('driver_assigned', 'Driver Assigned'),
        ('driver_arrived', 'Driver Arrived'),
        ('in_progress', 'Ride in Progress'),
        ('completed', 'Ride Completed'),
        ('cancelled_by_customer', 'Cancelled by Customer'),
        ('cancelled_by_driver', 'Cancelled by Driver'),
        ('cancelled_by_system', 'Cancelled by System'),
        ('no_driver_found', 'No Driver Found'),
    )
    
    RIDE_TYPES = (
        ('boda', 'Motorcycle Ride'),
        ('car', 'Car Ride'),
        ('delivery', 'Package Delivery'),
        ('express', 'Express Delivery'),
    )
    
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('card', 'Credit/Debit Card'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Parties involved
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='customer_rides'
    )
    driver = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='driver_rides'
    )
    
    # Ride details
    ride_type = models.CharField(max_length=20, choices=RIDE_TYPES, default='boda')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='requested')
    
    # Location information
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    pickup_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    pickup_address = models.TextField()
    pickup_landmark = models.CharField(max_length=200, blank=True)
    
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    destination_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    destination_address = models.TextField()
    destination_landmark = models.CharField(max_length=200, blank=True)
    
    # Rwanda-specific location fields
    pickup_province = models.CharField(max_length=100, blank=True)
    pickup_district = models.CharField(max_length=100, blank=True)
    pickup_sector = models.CharField(max_length=100, blank=True)
    
    destination_province = models.CharField(max_length=100, blank=True)
    destination_district = models.CharField(max_length=100, blank=True)
    destination_sector = models.CharField(max_length=100, blank=True)
    
    # Distance and pricing
    estimated_distance = models.DecimalField(max_digits=8, decimal_places=2)  # in kilometers
    actual_distance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    estimated_duration = models.PositiveIntegerField()  # in minutes
    actual_duration = models.PositiveIntegerField(null=True, blank=True)
    
    # Pricing in Rwanda Francs (RWF)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    distance_fare = models.DecimalField(max_digits=10, decimal_places=2)
    time_fare = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    surge_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('1.00'))
    total_fare = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Payment Pending'),
            ('processing', 'Payment Processing'),
            ('completed', 'Payment Completed'),
            ('failed', 'Payment Failed'),
            ('refunded', 'Payment Refunded'),
        ),
        default='pending'
    )
    
    # Special instructions and notes
    customer_notes = models.TextField(blank=True)
    driver_notes = models.TextField(blank=True)
    special_requirements = models.CharField(max_length=500, blank=True)
    
    # Ratings and feedback
    customer_rating = models.PositiveIntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    driver_rating = models.PositiveIntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    customer_feedback = models.TextField(blank=True)
    driver_feedback = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    driver_assigned_at = models.DateTimeField(null=True, blank=True)
    driver_arrived_at = models.DateTimeField(null=True, blank=True)
    ride_started_at = models.DateTimeField(null=True, blank=True)
    ride_ended_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Cancellation information
    cancellation_reason = models.CharField(max_length=500, blank=True)
    cancellation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        db_table = 'rides'
        verbose_name = 'Ride'
        verbose_name_plural = 'Rides'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['ride_type']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Ride {self.id} - {self.customer.full_name} to {self.destination_address[:50]}"
    
    @property
    def is_active(self):
        """Check if ride is currently active"""
        return self.status in ['requested', 'driver_assigned', 'driver_arrived', 'in_progress']
    
    @property
    def duration_minutes(self):
        """Calculate ride duration in minutes"""
        if self.ride_started_at and self.ride_ended_at:
            return int((self.ride_ended_at - self.ride_started_at).total_seconds() / 60)
        return None


class RideStatusHistory(models.Model):
    """
    Track all status changes for rides for audit and analytics
    """
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=30, choices=Ride.STATUS_CHOICES, blank=True)
    to_status = models.CharField(max_length=30, choices=Ride.STATUS_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ride_status_history'
        verbose_name = 'Ride Status History'
        verbose_name_plural = 'Ride Status Histories'
        ordering = ['-created_at']


class RideLocation(models.Model):
    """
    Track real-time location updates during rides
    """
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='ride_locations')
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    accuracy = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    speed = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # km/h
    heading = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # degrees
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ride_locations'
        verbose_name = 'Ride Location'
        verbose_name_plural = 'Ride Locations'
        indexes = [
            models.Index(fields=['ride', 'timestamp']),
        ]
        ordering = ['-timestamp']


class RideRequest(models.Model):
    """
    Track ride requests and driver responses
    """
    RESPONSE_STATUS = (
        ('pending', 'Pending Response'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    )
    
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='requests')
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ride_requests')
    
    # Driver location when request was sent
    driver_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    driver_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    distance_to_pickup = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_arrival_time = models.PositiveIntegerField()  # minutes
    
    status = models.CharField(max_length=20, choices=RESPONSE_STATUS, default='pending')
    response_time = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'ride_requests'
        verbose_name = 'Ride Request'
        verbose_name_plural = 'Ride Requests'
        indexes = [
            models.Index(fields=['ride', 'status']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['expires_at']),
        ]


class RideFare(models.Model):
    """
    Store ride fare calculations and breakdowns
    """
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='fare_breakdown')
    
    # Base pricing
    base_fare = models.DecimalField(max_digits=8, decimal_places=2)
    per_km_rate = models.DecimalField(max_digits=6, decimal_places=2)
    per_minute_rate = models.DecimalField(max_digits=6, decimal_places=2)
    
    # Distance and time charges
    distance_charge = models.DecimalField(max_digits=8, decimal_places=2)
    time_charge = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Additional charges
    surge_charge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    night_charge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    toll_charge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # Discounts
    promo_discount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    loyalty_discount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # Taxes (Rwanda VAT)
    vat_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('18.00'))
    
    # Final amounts
    subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ride_fares'
        verbose_name = 'Ride Fare'
        verbose_name_plural = 'Ride Fares'