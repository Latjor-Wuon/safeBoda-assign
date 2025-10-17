"""
Analytics serializers for SafeBoda Rwanda
Handle serialization of analytics data and reports
"""
from rest_framework import serializers
from .models import (
    AnalyticsReport, RideMetrics, DriverPerformanceMetrics,
    PopularRoute, CustomerInsight
)


class AnalyticsReportSerializer(serializers.ModelSerializer):
    """
    Serializer for analytics reports
    """
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = AnalyticsReport
        fields = [
            'id', 'report_type', 'title', 'start_date', 'end_date',
            'data', 'metadata', 'generated_at', 'generated_by',
            'generated_by_name'
        ]
        read_only_fields = ['id', 'generated_at', 'generated_by', 'generated_by_name']


class RideMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer for ride metrics
    """
    class Meta:
        model = RideMetrics
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class DriverPerformanceMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer for driver performance metrics
    """
    driver_name = serializers.CharField(source='driver.get_full_name', read_only=True)
    driver_email = serializers.CharField(source='driver.email', read_only=True)
    
    class Meta:
        model = DriverPerformanceMetrics
        fields = [
            'id', 'driver', 'driver_name', 'driver_email', 'date',
            'total_rides', 'completed_rides', 'cancelled_rides',
            'online_hours', 'acceptance_rate', 'completion_rate',
            'average_rating', 'gross_earnings', 'commission_paid',
            'net_earnings', 'total_distance', 'fuel_efficiency_score',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'driver_name', 'driver_email']


class PopularRouteSerializer(serializers.ModelSerializer):
    """
    Serializer for popular routes
    """
    route_description = serializers.SerializerMethodField()
    
    class Meta:
        model = PopularRoute
        fields = [
            'id', 'pickup_latitude', 'pickup_longitude', 'pickup_address',
            'pickup_district', 'destination_latitude', 'destination_longitude',
            'destination_address', 'destination_district', 'ride_count',
            'average_fare', 'average_duration', 'average_distance',
            'peak_hour', 'weekly_pattern', 'last_updated', 'first_recorded',
            'route_description'
        ]
        read_only_fields = ['id', 'last_updated', 'first_recorded', 'route_description']
    
    def get_route_description(self, obj):
        return f"{obj.pickup_district} → {obj.destination_district}"


class CustomerInsightSerializer(serializers.ModelSerializer):
    """
    Serializer for customer insights
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    
    class Meta:
        model = CustomerInsight
        fields = [
            'id', 'customer', 'customer_name', 'customer_email',
            'total_rides', 'total_spent', 'average_ride_value',
            'preferred_payment_method', 'preferred_ride_type',
            'most_common_pickup_district', 'most_common_destination_district',
            'peak_usage_hour', 'weekend_vs_weekday_ratio',
            'days_since_first_ride', 'days_since_last_ride',
            'loyalty_score', 'average_rating_given',
            'last_updated', 'created_at'
        ]
        read_only_fields = [
            'id', 'customer_name', 'customer_email',
            'last_updated', 'created_at'
        ]


class AnalyticsQuerySerializer(serializers.Serializer):
    """
    Serializer for analytics query parameters
    """
    start_date = serializers.DateField(required=True, help_text="Start date for analytics (YYYY-MM-DD)")
    end_date = serializers.DateField(required=True, help_text="End date for analytics (YYYY-MM-DD)")
    driver_id = serializers.UUIDField(required=False, help_text="Specific driver ID for driver performance analysis")
    limit = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100, 
                                   help_text="Limit for results (1-100)")
    
    def validate(self, data):
        """
        Validate date range
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date must be before or equal to end date")
            
            # Limit to maximum 1 year range for performance
            if (end_date - start_date).days > 365:
                raise serializers.ValidationError("Date range cannot exceed 365 days")
        
        return data


class ReportGenerationSerializer(serializers.Serializer):
    """
    Serializer for report generation requests
    """
    REPORT_TYPE_CHOICES = [
        ('ride_summary', 'Ride Summary'),
        ('revenue_report', 'Revenue Report'),
        ('driver_performance', 'Driver Performance'),
        ('popular_routes', 'Popular Routes'),
        ('customer_insights', 'Customer Insights'),
        ('time_patterns', 'Time Patterns'),
    ]
    
    report_type = serializers.ChoiceField(choices=REPORT_TYPE_CHOICES, required=True)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    title = serializers.CharField(max_length=200, required=False, 
                                 help_text="Optional custom title for the report")
    
    def validate(self, data):
        """
        Validate report generation parameters
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date must be before or equal to end date")
            
            if (end_date - start_date).days > 365:
                raise serializers.ValidationError("Report date range cannot exceed 365 days")
        
        return data