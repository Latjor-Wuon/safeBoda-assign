"""
Analytics services for SafeBoda Rwanda
Business intelligence and data analysis services
"""
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List, Any
import calendar

from bookings.models import Ride
from authentication.models import User, DriverProfile
from .models import (
    RideMetrics, DriverPerformanceMetrics, PopularRoute,
    CustomerInsight, AnalyticsReport
)


class AnalyticsService:
    """
    Core analytics service for SafeBoda Rwanda platform
    """
    
    @staticmethod
    def get_ride_summary(start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Get comprehensive ride summary for date range
        """
        rides_qs = Ride.objects.filter(
            created_at__date__range=(start_date, end_date)
        )
        
        total_rides = rides_qs.count()
        completed_rides = rides_qs.filter(status='completed').count()
        cancelled_rides = rides_qs.filter(
            status__in=['cancelled_by_customer', 'cancelled_by_driver', 'cancelled_by_system']
        ).count()
        
        # Revenue calculations
        revenue_data = rides_qs.filter(status='completed').aggregate(
            total_revenue=Sum('total_fare'),
            average_fare=Avg('total_fare')
        )
        
        # Distance and duration
        distance_data = rides_qs.filter(status='completed').aggregate(
            total_distance=Sum('actual_distance'),
            average_distance=Avg('actual_distance'),
            total_duration=Sum('actual_duration'),
            average_duration=Avg('actual_duration')
        )
        
        # Driver metrics
        active_drivers = rides_qs.values('driver').distinct().count()
        unique_customers = rides_qs.values('customer').distinct().count()
        
        # Peak hours analysis
        hourly_distribution = []
        for hour in range(24):
            rides_in_hour = rides_qs.filter(
                created_at__hour=hour
            ).count()
            hourly_distribution.append({
                'hour': hour,
                'rides': rides_in_hour,
                'percentage': (rides_in_hour / total_rides * 100) if total_rides > 0 else 0
            })
        
        peak_hour = max(hourly_distribution, key=lambda x: x['rides'])['hour'] if hourly_distribution else 0
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days + 1
            },
            'ride_counts': {
                'total_rides': total_rides,
                'completed_rides': completed_rides,
                'cancelled_rides': cancelled_rides,
                'completion_rate': (completed_rides / total_rides * 100) if total_rides > 0 else 0,
                'cancellation_rate': (cancelled_rides / total_rides * 100) if total_rides > 0 else 0
            },
            'revenue': {
                'total_revenue': float(revenue_data['total_revenue'] or 0),
                'average_fare': float(revenue_data['average_fare'] or 0),
                'revenue_per_day': float((revenue_data['total_revenue'] or 0) / ((end_date - start_date).days + 1))
            },
            'distance_duration': {
                'total_distance_km': float(distance_data['total_distance'] or 0),
                'average_distance_km': float(distance_data['average_distance'] or 0),
                'total_duration_minutes': int(distance_data['total_duration'] or 0),
                'average_duration_minutes': float(distance_data['average_duration'] or 0)
            },
            'participants': {
                'active_drivers': active_drivers,
                'unique_customers': unique_customers,
                'rides_per_driver': (completed_rides / active_drivers) if active_drivers > 0 else 0
            },
            'time_patterns': {
                'peak_hour': peak_hour,
                'hourly_distribution': hourly_distribution
            }
        }
    
    @staticmethod
    def get_revenue_analysis(start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Detailed revenue analysis with trends and breakdowns
        """
        rides_qs = Ride.objects.filter(
            created_at__date__range=(start_date, end_date),
            status='completed'
        )
        
        # Daily revenue breakdown
        daily_revenue = []
        current_date = start_date
        while current_date <= end_date:
            day_revenue = rides_qs.filter(
                created_at__date=current_date
            ).aggregate(Sum('total_fare'))['total_fare__sum'] or 0
            
            daily_revenue.append({
                'date': current_date.isoformat(),
                'revenue': float(day_revenue),
                'day_name': calendar.day_name[current_date.weekday()]
            })
            current_date += timedelta(days=1)
        
        # Payment method breakdown
        payment_breakdown = rides_qs.values('payment_method').annotate(
            count=Count('id'),
            revenue=Sum('total_fare')
        ).order_by('-revenue')
        
        # Ride type revenue breakdown
        ride_type_breakdown = rides_qs.values('ride_type').annotate(
            count=Count('id'),
            revenue=Sum('total_fare'),
            avg_fare=Avg('total_fare')
        ).order_by('-revenue')
        
        # Commission calculation (assuming 20% commission)
        total_revenue = rides_qs.aggregate(Sum('total_fare'))['total_fare__sum'] or 0
        commission_rate = Decimal('0.20')
        total_commission = total_revenue * commission_rate
        driver_earnings = total_revenue - total_commission
        
        return {
            'summary': {
                'total_revenue': float(total_revenue),
                'total_commission': float(total_commission),
                'driver_earnings': float(driver_earnings),
                'commission_rate': float(commission_rate * 100),
                'average_daily_revenue': float(total_revenue / len(daily_revenue)) if daily_revenue else 0
            },
            'trends': {
                'daily_revenue': daily_revenue,
                'growth_rate': 0  # Would calculate based on previous period comparison
            },
            'breakdowns': {
                'by_payment_method': [
                    {
                        'payment_method': item['payment_method'],
                        'rides': item['count'],
                        'revenue': float(item['revenue']),
                        'percentage': float(item['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
                    } for item in payment_breakdown
                ],
                'by_ride_type': [
                    {
                        'ride_type': item['ride_type'],
                        'rides': item['count'],
                        'revenue': float(item['revenue']),
                        'average_fare': float(item['avg_fare']),
                        'percentage': float(item['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
                    } for item in ride_type_breakdown
                ]
            }
        }
    
    @staticmethod
    def get_driver_performance_analysis(start_date: date, end_date: date, 
                                      driver_id: str = None) -> Dict[str, Any]:
        """
        Analyze driver performance metrics
        """
        drivers_filter = Q(role='driver')
        if driver_id:
            drivers_filter &= Q(id=driver_id)
        
        drivers = User.objects.filter(drivers_filter)
        driver_stats = []
        
        for driver in drivers:
            driver_rides = Ride.objects.filter(
                driver=driver,
                created_at__date__range=(start_date, end_date)
            )
            
            total_rides = driver_rides.count()
            completed_rides = driver_rides.filter(status='completed').count()
            cancelled_rides = driver_rides.filter(
                status__in=['cancelled_by_driver', 'cancelled_by_system']
            ).count()
            
            earnings_data = driver_rides.filter(status='completed').aggregate(
                total_earnings=Sum('total_fare')
            )
            
            rating_data = driver_rides.filter(
                customer_rating__isnull=False
            ).aggregate(
                avg_rating=Avg('customer_rating'),
                rating_count=Count('customer_rating')
            )
            
            driver_stats.append({
                'driver_id': str(driver.id),
                'driver_name': driver.get_full_name(),
                'email': driver.email,
                'phone_number': driver.phone_number,
                'metrics': {
                    'total_rides': total_rides,
                    'completed_rides': completed_rides,
                    'cancelled_rides': cancelled_rides,
                    'completion_rate': (completed_rides / total_rides * 100) if total_rides > 0 else 0,
                    'cancellation_rate': (cancelled_rides / total_rides * 100) if total_rides > 0 else 0,
                    'gross_earnings': float(earnings_data['total_earnings'] or 0),
                    'average_rating': float(rating_data['avg_rating'] or 0),
                    'rating_count': rating_data['rating_count'] or 0,
                    'earnings_per_ride': float((earnings_data['total_earnings'] or 0) / completed_rides) if completed_rides > 0 else 0
                }
            })
        
        # Sort by total earnings descending
        driver_stats.sort(key=lambda x: x['metrics']['gross_earnings'], reverse=True)
        
        # Calculate platform averages
        total_platform_rides = sum(d['metrics']['total_rides'] for d in driver_stats)
        total_platform_earnings = sum(d['metrics']['gross_earnings'] for d in driver_stats)
        
        platform_averages = {
            'avg_rides_per_driver': total_platform_rides / len(driver_stats) if driver_stats else 0,
            'avg_earnings_per_driver': total_platform_earnings / len(driver_stats) if driver_stats else 0,
            'avg_completion_rate': sum(d['metrics']['completion_rate'] for d in driver_stats) / len(driver_stats) if driver_stats else 0
        }
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'driver_count': len(driver_stats),
            'platform_averages': platform_averages,
            'driver_performance': driver_stats[:20] if not driver_id else driver_stats  # Top 20 or specific driver
        }
    
    @staticmethod
    def get_popular_routes_analysis(limit: int = 20) -> Dict[str, Any]:
        """
        Analyze most popular pickup-destination combinations
        """
        # Aggregate routes from completed rides in the last 30 days
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        
        routes = Ride.objects.filter(
            status='completed',
            created_at__date__gte=thirty_days_ago
        ).values(
            'pickup_district', 'destination_district',
            'pickup_address', 'destination_address'
        ).annotate(
            ride_count=Count('id'),
            avg_fare=Avg('total_fare'),
            avg_distance=Avg('actual_distance'),
            avg_duration=Avg('actual_duration')
        ).order_by('-ride_count')[:limit]
        
        popular_routes = []
        for route in routes:
            popular_routes.append({
                'route': f"{route['pickup_district']} → {route['destination_district']}",
                'pickup_location': {
                    'district': route['pickup_district'],
                    'address': route['pickup_address']
                },
                'destination_location': {
                    'district': route['destination_district'],
                    'address': route['destination_address']
                },
                'metrics': {
                    'ride_count': route['ride_count'],
                    'average_fare': float(route['avg_fare'] or 0),
                    'average_distance_km': float(route['avg_distance'] or 0),
                    'average_duration_minutes': float(route['avg_duration'] or 0)
                }
            })
        
        # District-level analysis
        district_popularity = Ride.objects.filter(
            status='completed',
            created_at__date__gte=thirty_days_ago
        ).values('pickup_district').annotate(
            pickup_count=Count('id')
        ).order_by('-pickup_count')[:10]
        
        destination_popularity = Ride.objects.filter(
            status='completed',
            created_at__date__gte=thirty_days_ago
        ).values('destination_district').annotate(
            destination_count=Count('id')
        ).order_by('-destination_count')[:10]
        
        return {
            'analysis_period': f"Last 30 days (since {thirty_days_ago.isoformat()})",
            'popular_routes': popular_routes,
            'district_analysis': {
                'top_pickup_districts': [
                    {
                        'district': item['pickup_district'],
                        'pickup_count': item['pickup_count']
                    } for item in district_popularity
                ],
                'top_destination_districts': [
                    {
                        'district': item['destination_district'],
                        'destination_count': item['destination_count']
                    } for item in destination_popularity
                ]
            }
        }
    
    @staticmethod
    def get_customer_insights_analysis() -> Dict[str, Any]:
        """
        Analyze customer behavior and preferences
        """
        # Customer ride patterns
        customer_stats = Ride.objects.filter(
            status='completed'
        ).values('customer').annotate(
            total_rides=Count('id'),
            total_spent=Sum('total_fare'),
            avg_ride_value=Avg('total_fare')
        ).order_by('-total_spent')
        
        # Segment customers
        segments = {
            'high_value': customer_stats.filter(total_spent__gte=50000).count(),  # 50k RWF+
            'medium_value': customer_stats.filter(
                total_spent__gte=20000, total_spent__lt=50000
            ).count(),
            'low_value': customer_stats.filter(total_spent__lt=20000).count(),
        }
        
        # Payment method preferences
        payment_preferences = Ride.objects.filter(
            status='completed'
        ).values('payment_method').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Ride type preferences
        ride_type_preferences = Ride.objects.filter(
            status='completed'
        ).values('ride_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Time patterns
        hourly_usage = []
        for hour in range(24):
            usage = Ride.objects.filter(
                status='completed',
                created_at__hour=hour
            ).count()
            hourly_usage.append({
                'hour': hour,
                'usage_count': usage
            })
        
        peak_usage_hour = max(hourly_usage, key=lambda x: x['usage_count'])['hour']
        
        return {
            'customer_segments': {
                'total_customers': len(customer_stats),
                'high_value_customers': segments['high_value'],
                'medium_value_customers': segments['medium_value'],
                'low_value_customers': segments['low_value']
            },
            'preferences': {
                'payment_methods': [
                    {
                        'method': item['payment_method'],
                        'usage_count': item['count'],
                        'percentage': item['count'] / sum(p['count'] for p in payment_preferences) * 100
                    } for item in payment_preferences
                ],
                'ride_types': [
                    {
                        'type': item['ride_type'],
                        'usage_count': item['count'],
                        'percentage': item['count'] / sum(r['count'] for r in ride_type_preferences) * 100
                    } for item in ride_type_preferences
                ]
            },
            'usage_patterns': {
                'peak_hour': peak_usage_hour,
                'hourly_distribution': hourly_usage
            },
            'top_customers': [
                {
                    'customer_id': str(item['customer']),
                    'total_rides': item['total_rides'],
                    'total_spent': float(item['total_spent']),
                    'average_ride_value': float(item['avg_ride_value'])
                } for item in customer_stats[:20]
            ]
        }
    
    @staticmethod
    def get_time_patterns_analysis() -> Dict[str, Any]:
        """
        Analyze ride patterns by time, day, and season
        """
        # Hourly patterns
        hourly_patterns = []
        for hour in range(24):
            rides = Ride.objects.filter(created_at__hour=hour).count()
            hourly_patterns.append({
                'hour': f"{hour:02d}:00",
                'ride_count': rides,
                'is_peak': hour in [7, 8, 17, 18, 19]  # Morning and evening rush hours
            })
        
        # Daily patterns (last 7 days)
        daily_patterns = []
        for i in range(7):
            day_date = timezone.now().date() - timedelta(days=i)
            rides = Ride.objects.filter(created_at__date=day_date).count()
            daily_patterns.append({
                'date': day_date.isoformat(),
                'day_name': calendar.day_name[day_date.weekday()],
                'ride_count': rides
            })
        
        # Weekly patterns (day of week analysis)
        weekly_patterns = []
        for day_num in range(7):
            day_name = calendar.day_name[day_num]
            rides = Ride.objects.filter(created_at__week_day=(day_num + 2) % 7 + 1).count()
            weekly_patterns.append({
                'day_name': day_name,
                'ride_count': rides,
                'is_weekend': day_num in [5, 6]  # Saturday, Sunday
            })
        
        return {
            'hourly_patterns': hourly_patterns,
            'daily_patterns': daily_patterns,
            'weekly_patterns': weekly_patterns,
            'insights': {
                'peak_hours': [p['hour'] for p in hourly_patterns if p['is_peak']],
                'busiest_day': max(weekly_patterns, key=lambda x: x['ride_count'])['day_name'],
                'weekend_vs_weekday_ratio': sum(p['ride_count'] for p in weekly_patterns if p['is_weekend']) / 
                                          sum(p['ride_count'] for p in weekly_patterns if not p['is_weekend']) 
                                          if sum(p['ride_count'] for p in weekly_patterns if not p['is_weekend']) > 0 else 0
            }
        }
    
    @staticmethod
    def generate_report(report_type: str, start_date: date, end_date: date, 
                       user: User = None) -> AnalyticsReport:
        """
        Generate and save analytics report
        """
        report_generators = {
            'ride_summary': AnalyticsService.get_ride_summary,
            'revenue_report': AnalyticsService.get_revenue_analysis,
            'driver_performance': AnalyticsService.get_driver_performance_analysis,
            'popular_routes': lambda s, e: AnalyticsService.get_popular_routes_analysis(),
            'customer_insights': lambda s, e: AnalyticsService.get_customer_insights_analysis(),
            'time_patterns': lambda s, e: AnalyticsService.get_time_patterns_analysis()
        }
        
        if report_type not in report_generators:
            raise ValueError(f"Unknown report type: {report_type}")
        
        generator = report_generators[report_type]
        data = generator(start_date, end_date)
        
        title_map = {
            'ride_summary': 'Ride Summary Report',
            'revenue_report': 'Revenue Analysis Report',
            'driver_performance': 'Driver Performance Report',
            'popular_routes': 'Popular Routes Analysis',
            'customer_insights': 'Customer Insights Report',
            'time_patterns': 'Time Patterns Analysis'
        }
        
        report = AnalyticsReport.objects.create(
            report_type=report_type,
            title=title_map[report_type],
            start_date=start_date,
            end_date=end_date,
            data=data,
            metadata={
                'generated_at': timezone.now().isoformat(),
                'generator_version': '1.0',
                'data_points': len(str(data))
            },
            generated_by=user
        )
        
        return report