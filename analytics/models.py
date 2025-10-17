"""
Analytics models for SafeBoda Rwanda
Track business metrics, performance, and revenue analytics
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class AnalyticsReport(models.Model):
    """
    Store pre-computed analytics reports for performance
    """
    REPORT_TYPES = (
        ('ride_summary', 'Ride Summary'),
        ('revenue_report', 'Revenue Report'),
        ('driver_performance', 'Driver Performance'),
        ('customer_insights', 'Customer Insights'),
        ('popular_routes', 'Popular Routes'),
        ('time_patterns', 'Time Patterns'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    
    # Time period
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Report data (JSON format for flexibility)
    data = models.JSONField()
    metadata = models.JSONField(default=dict)
    
    # Generation info
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['report_type', 'start_date', 'end_date']),
            models.Index(fields=['generated_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"


class RideMetrics(models.Model):
    """
    Daily/hourly aggregated ride metrics for faster analytics
    """
    AGGREGATION_TYPES = (
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    hour = models.PositiveIntegerField(null=True, blank=True)  # 0-23 for hourly data
    aggregation_type = models.CharField(max_length=20, choices=AGGREGATION_TYPES)
    
    # Ride counts
    total_rides = models.PositiveIntegerField(default=0)
    completed_rides = models.PositiveIntegerField(default=0)
    cancelled_rides = models.PositiveIntegerField(default=0)
    
    # Revenue metrics (in RWF)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    average_ride_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Distance and time metrics
    total_distance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    average_distance = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    total_duration = models.PositiveIntegerField(default=0)  # in minutes
    average_duration = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    
    # Driver metrics
    active_drivers = models.PositiveIntegerField(default=0)
    unique_customers = models.PositiveIntegerField(default=0)
    
    # Rwanda-specific metrics
    kigali_rides = models.PositiveIntegerField(default=0)
    province_breakdown = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['date', 'hour', 'aggregation_type']
        ordering = ['-date', '-hour']
        indexes = [
            models.Index(fields=['date', 'aggregation_type']),
            models.Index(fields=['date', 'hour']),
        ]
    
    def __str__(self):
        if self.hour is not None:
            return f"Metrics for {self.date} {self.hour:02d}:00"
        return f"Metrics for {self.date} ({self.aggregation_type})"


class DriverPerformanceMetrics(models.Model):
    """
    Track individual driver performance metrics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='performance_metrics')
    date = models.DateField()
    
    # Ride statistics
    total_rides = models.PositiveIntegerField(default=0)
    completed_rides = models.PositiveIntegerField(default=0)
    cancelled_rides = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    online_hours = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    
    # Earnings
    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    commission_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Distance metrics
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    fuel_efficiency_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['driver', 'date']
        ordering = ['-date', '-gross_earnings']
        indexes = [
            models.Index(fields=['driver', 'date']),
            models.Index(fields=['date', 'gross_earnings']),
            models.Index(fields=['completion_rate']),
        ]
    
    def __str__(self):
        return f"{self.driver.get_full_name()} - {self.date}"


class PopularRoute(models.Model):
    """
    Track popular pickup/destination combinations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Route information
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    pickup_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    pickup_address = models.TextField()
    pickup_district = models.CharField(max_length=100)
    
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    destination_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    destination_address = models.TextField()
    destination_district = models.CharField(max_length=100)
    
    # Metrics
    ride_count = models.PositiveIntegerField(default=1)
    average_fare = models.DecimalField(max_digits=10, decimal_places=2)
    average_duration = models.DecimalField(max_digits=6, decimal_places=2)
    average_distance = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Time patterns
    peak_hour = models.PositiveIntegerField()  # Most common hour (0-23)
    weekly_pattern = models.JSONField(default=dict)  # Day-of-week breakdown
    
    # Tracking
    last_updated = models.DateTimeField(auto_now=True)
    first_recorded = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-ride_count', '-last_updated']
        indexes = [
            models.Index(fields=['pickup_district', 'destination_district']),
            models.Index(fields=['ride_count']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"{self.pickup_district} → {self.destination_district} ({self.ride_count} rides)"


class CustomerInsight(models.Model):
    """
    Store customer behavior analytics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='insights')
    
    # Ride behavior
    total_rides = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    average_ride_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Preferences
    preferred_payment_method = models.CharField(max_length=20, blank=True)
    preferred_ride_type = models.CharField(max_length=20, blank=True)
    most_common_pickup_district = models.CharField(max_length=100, blank=True)
    most_common_destination_district = models.CharField(max_length=100, blank=True)
    
    # Behavior patterns
    peak_usage_hour = models.PositiveIntegerField(null=True, blank=True)
    weekend_vs_weekday_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Loyalty metrics
    days_since_first_ride = models.PositiveIntegerField(default=0)
    days_since_last_ride = models.PositiveIntegerField(default=0)
    loyalty_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Rating given by customer
    average_rating_given = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-total_spent', '-total_rides']
        indexes = [
            models.Index(fields=['total_rides', 'total_spent']),
            models.Index(fields=['loyalty_score']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"Insights for {self.customer.get_full_name()}"