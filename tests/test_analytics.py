"""
Test analytics functionality for SafeBoda Rwanda
Comprehensive testing of analytics endpoints and services
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from analytics.models import (
    AnalyticsReport, RideMetrics, DriverPerformanceMetrics, 
    PopularRoute, CustomerInsight
)
from analytics.services import AnalyticsService
from bookings.models import Ride
from authentication.models import DriverProfile

User = get_user_model()


class AnalyticsModelsTests(TestCase):
    """Test analytics models"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@safeboda.rw',
            username='admin',
            password='AdminPass123!',
            phone_number='+250788000000',
            national_id='1234567890123456',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        
        self.customer = User.objects.create_user(
            email='customer@test.com',
            username='customer',
            password='CustomerPass123!',
            phone_number='+250788111111',
            national_id='1111111111111111',
            first_name='Test',
            last_name='Customer',
            role='customer'
        )
    
    def test_analytics_report_creation(self):
        """Test creating analytics report"""
        report_data = {
            'total_rides': 150,
            'revenue': 45000.0,
            'completion_rate': 94.5
        }
        
        report = AnalyticsReport.objects.create(
            report_type='ride_summary',
            title='Weekly Ride Summary',
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            data=report_data,
            generated_by=self.admin_user
        )
        
        self.assertEqual(report.report_type, 'ride_summary')
        self.assertEqual(report.data['total_rides'], 150)
        self.assertEqual(report.generated_by, self.admin_user)
    
    def test_ride_metrics_creation(self):
        """Test creating ride metrics"""
        metrics = RideMetrics.objects.create(
            date=date.today(),
            aggregation_type='daily',
            total_rides=25,
            completed_rides=23,
            cancelled_rides=2,
            total_revenue=Decimal('12500.00'),
            average_ride_value=Decimal('543.48'),
            total_distance=Decimal('245.60'),
            active_drivers=12,
            unique_customers=18
        )
        
        self.assertEqual(metrics.total_rides, 25)
        self.assertEqual(metrics.completion_rate, 92.0)  # 23/25 * 100
        self.assertEqual(float(metrics.total_revenue), 12500.00)
    
    def test_driver_performance_metrics(self):
        """Test driver performance metrics"""
        driver = User.objects.create_user(
            email='driver@test.com',
            username='driver_test',
            password='DriverPass123!',
            phone_number='+250788222222',
            national_id='2222222222222222',
            first_name='Test',
            last_name='Driver',
            role='driver'
        )
        
        performance = DriverPerformanceMetrics.objects.create(
            driver=driver,
            date=date.today(),
            total_rides=8,
            completed_rides=7,
            cancelled_rides=1,
            online_hours=Decimal('8.5'),
            acceptance_rate=Decimal('87.5'),
            completion_rate=Decimal('87.5'),
            average_rating=Decimal('4.6'),
            gross_earnings=Decimal('3400.00'),
            commission_paid=Decimal('680.00'),
            net_earnings=Decimal('2720.00'),
            total_distance=Decimal('95.4')
        )
        
        self.assertEqual(performance.driver, driver)
        self.assertEqual(performance.completion_rate, Decimal('87.5'))
        self.assertEqual(float(performance.net_earnings), 2720.00)
    
    def test_customer_insight_creation(self):
        """Test customer insight model"""
        insight = CustomerInsight.objects.create(
            customer=self.customer,
            total_rides=45,
            total_spent=Decimal('67500.00'),
            average_ride_value=Decimal('1500.00'),
            preferred_payment_method='mtn_momo',
            preferred_ride_type='boda',
            most_common_pickup_district='Gasabo',
            most_common_destination_district='Nyarugenge',
            peak_usage_hour=8,
            weekend_vs_weekday_ratio=Decimal('0.35'),
            days_since_first_ride=120,
            days_since_last_ride=2,
            loyalty_score=Decimal('85.5'),
            average_rating_given=Decimal('4.3')
        )
        
        self.assertEqual(insight.customer, self.customer)
        self.assertEqual(insight.total_rides, 45)
        self.assertEqual(insight.preferred_payment_method, 'mtn_momo')
        self.assertEqual(float(insight.loyalty_score), 85.5)


class AnalyticsServicesTests(TestCase):
    """Test analytics service methods"""
    
    def setUp(self):
        """Set up test data"""
        self.customer = User.objects.create_user(
            email='customer@analytics.test',
            username='customer_analytics',
            password='TestPass123!',
            phone_number='+250788333333',
            national_id='3333333333333333',
            first_name='Analytics',
            last_name='Customer',
            role='customer'
        )
        
        self.driver = User.objects.create_user(
            email='driver@analytics.test',
            username='driver_analytics',
            password='TestPass123!',
            phone_number='+250788444444',
            national_id='4444444444444444',
            first_name='Analytics',
            last_name='Driver',
            role='driver'
        )
        
        # Create driver profile
        self.driver_profile = DriverProfile.objects.create(
            user=self.driver,
            license_number='RW987654321',
            license_expiry_date=date.today() + timedelta(days=365),
            license_category='B',
            vehicle_type='motorcycle',
            vehicle_plate_number='RAB 456B',
            vehicle_make='Yamaha',
            vehicle_model='FZ 150',
            vehicle_year=2021,
            vehicle_color='Blue',
            insurance_number='INS987654321',
            insurance_expiry_date=date.today() + timedelta(days=365),
            vehicle_inspection_date=date.today() - timedelta(days=30),
            vehicle_inspection_expiry=date.today() + timedelta(days=365),
            is_online=True
        )
        
        # Create test rides
        self.create_test_rides()
    
    def create_test_rides(self):
        """Create sample rides for analytics testing"""
        base_date = date.today() - timedelta(days=3)
        
        for i in range(5):
            Ride.objects.create(
                customer=self.customer,
                driver=self.driver,
                pickup_address=f'Pickup Location {i+1}',
                destination_address=f'Destination {i+1}',
                pickup_latitude=Decimal('-1.9441'),
                pickup_longitude=Decimal('30.0619'),
                destination_latitude=Decimal('-1.9706'),
                destination_longitude=Decimal('30.1044'),
                estimated_distance=Decimal('10.5'),
                estimated_duration=20,
                base_fare=Decimal('1000.00'),
                distance_fare=Decimal('2100.00'),
                total_fare=Decimal('3100.00'),
                payment_method='mtn_momo',
                status='completed' if i < 4 else 'cancelled_by_customer',
                pickup_district='Gasabo',
                destination_district='Nyarugenge'
            )
    
    def test_ride_summary_analysis(self):
        """Test ride summary analytics service"""
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        summary = AnalyticsService.get_ride_summary(start_date, end_date)
        
        self.assertIn('ride_counts', summary)
        self.assertIn('revenue_metrics', summary)
        self.assertIn('distance_metrics', summary)
        self.assertIn('participants', summary)
        
        # Check ride counts
        self.assertEqual(summary['ride_counts']['total_rides'], 5)
        self.assertEqual(summary['ride_counts']['completed_rides'], 4)
        self.assertEqual(summary['ride_counts']['cancelled_rides'], 1)
        self.assertEqual(summary['ride_counts']['completion_rate'], 80.0)
    
    def test_revenue_analysis(self):
        """Test revenue analytics service"""
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        revenue_data = AnalyticsService.get_revenue_analysis(start_date, end_date)
        
        self.assertIn('summary', revenue_data)
        self.assertIn('payment_methods', revenue_data)
        self.assertIn('daily_trends', revenue_data)
        
        # Check revenue summary
        expected_revenue = 4 * 3100.00  # 4 completed rides at 3100 each
        self.assertEqual(float(revenue_data['summary']['total_revenue']), expected_revenue)
    
    def test_driver_performance_analysis(self):
        """Test driver performance analytics"""
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        performance = AnalyticsService.get_driver_performance_analysis(
            start_date, end_date, str(self.driver.id)
        )
        
        self.assertIn('driver_metrics', performance)
        self.assertIn('platform_averages', performance)
        
        # Check driver metrics
        driver_data = performance['driver_metrics'][0]
        self.assertEqual(driver_data['driver_id'], str(self.driver.id))
        self.assertEqual(driver_data['total_rides'], 5)
        self.assertEqual(driver_data['completed_rides'], 4)
    
    def test_popular_routes_analysis(self):
        """Test popular routes analytics"""
        routes_data = AnalyticsService.get_popular_routes_analysis(10)
        
        self.assertIn('popular_routes', routes_data)
        self.assertIn('district_summary', routes_data)
        
        # Should find our Gasabo -> Nyarugenge route
        routes = routes_data['popular_routes']
        if routes:  # Only check if routes exist
            route = routes[0]
            self.assertEqual(route['pickup_district'], 'Gasabo')
            self.assertEqual(route['destination_district'], 'Nyarugenge')
            self.assertEqual(route['ride_count'], 5)
    
    def test_customer_insights_analysis(self):
        """Test customer insights analytics"""
        insights = AnalyticsService.get_customer_insights_analysis()
        
        self.assertIn('customer_segments', insights)
        self.assertIn('payment_preferences', insights)
        self.assertIn('top_customers', insights)
        
        # Check customer segments
        segments = insights['customer_segments']
        self.assertGreaterEqual(segments['total_customers'], 1)
    
    def test_time_patterns_analysis(self):
        """Test time patterns analytics"""
        patterns = AnalyticsService.get_time_patterns_analysis()
        
        self.assertIn('hourly_distribution', patterns)
        self.assertIn('daily_patterns', patterns)
        self.assertIn('insights', patterns)
        
        # Check that we have some hourly data
        hourly = patterns['hourly_distribution']
        self.assertIsInstance(hourly, list)
        self.assertEqual(len(hourly), 24)  # 24 hours


class AnalyticsAPITests(APITestCase):
    """Test analytics API endpoints"""
    
    def setUp(self):
        """Set up test data and authentication"""
        self.admin_user = User.objects.create_user(
            email='admin@analytics.api',
            username='admin_api',
            password='AdminPass123!',
            phone_number='+250788555555',
            national_id='5555555555555555',
            first_name='Admin',
            last_name='API',
            role='admin'
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_ride_summary_endpoint(self):
        """Test ride summary analytics endpoint"""
        url = reverse('analytics:ride_summary')
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        response = self.client.get(url, {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('ride_counts', data['data'])
    
    def test_revenue_analytics_endpoint(self):
        """Test revenue analytics endpoint"""
        url = reverse('analytics:revenue')
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        response = self.client.get(url, {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('summary', data['data'])
    
    def test_driver_performance_endpoint(self):
        """Test driver performance analytics endpoint"""
        url = reverse('analytics:driver_performance')
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        response = self.client.get(url, {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('data', data)
    
    def test_popular_routes_endpoint(self):
        """Test popular routes analytics endpoint"""
        url = reverse('analytics:popular_routes')
        
        response = self.client.get(url, {'limit': 5})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('popular_routes', data['data'])
    
    def test_customer_insights_endpoint(self):
        """Test customer insights analytics endpoint"""
        url = reverse('analytics:customer_insights')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('customer_segments', data['data'])
    
    def test_time_patterns_endpoint(self):
        """Test time patterns analytics endpoint"""
        url = reverse('analytics:time_patterns')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('hourly_distribution', data['data'])
    
    def test_dashboard_endpoint(self):
        """Test analytics dashboard endpoint"""
        url = reverse('analytics:dashboard')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('quick_stats', data['data'])
        self.assertIn('trends', data['data'])
    
    def test_generate_report_endpoint(self):
        """Test report generation endpoint"""
        url = reverse('analytics:generate_report')
        
        report_data = {
            'report_type': 'ride_summary',
            'start_date': (date.today() - timedelta(days=7)).isoformat(),
            'end_date': date.today().isoformat(),
            'title': 'Test Weekly Report'
        }
        
        response = self.client.post(url, report_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('report', data)
        self.assertEqual(data['report']['title'], 'Test Weekly Report')
    
    def test_analytics_authentication_required(self):
        """Test that analytics endpoints require authentication"""
        # Remove authentication
        self.client.credentials()
        
        url = reverse('analytics:ride_summary')
        response = self.client.get(url, {
            'start_date': date.today().isoformat(),
            'end_date': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_invalid_date_range(self):
        """Test analytics endpoint with invalid date range"""
        url = reverse('analytics:ride_summary')
        
        # Start date after end date
        response = self.client.get(url, {
            'start_date': date.today().isoformat(),
            'end_date': (date.today() - timedelta(days=1)).isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data.get('success', True))


class AnalyticsPerformanceTests(TestCase):
    """Test analytics performance and caching"""
    
    def setUp(self):
        """Set up performance test data"""
        self.admin_user = User.objects.create_user(
            email='admin@performance.test',
            username='admin_perf',
            password='AdminPass123!',
            phone_number='+250788666666',
            national_id='6666666666666666',
            first_name='Performance',
            last_name='Admin',
            role='admin'
        )
    
    def test_analytics_service_performance(self):
        """Test analytics service method performance"""
        import time
        
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Test ride summary performance
        start_time = time.time()
        summary = AnalyticsService.get_ride_summary(start_date, end_date)
        execution_time = time.time() - start_time
        
        self.assertLess(execution_time, 2.0)  # Should complete in under 2 seconds
        self.assertIsInstance(summary, dict)
        
        # Test revenue analysis performance
        start_time = time.time()
        revenue = AnalyticsService.get_revenue_analysis(start_date, end_date)
        execution_time = time.time() - start_time
        
        self.assertLess(execution_time, 2.0)
        self.assertIsInstance(revenue, dict)
    
    def test_multiple_concurrent_requests(self):
        """Test handling multiple analytics requests"""
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        def run_analytics():
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            return AnalyticsService.get_ride_summary(start_date, end_date)
        
        # Run 5 concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_analytics) for _ in range(5)]
            results = [future.result() for future in futures]
        
        total_time = time.time() - start_time
        
        self.assertEqual(len(results), 5)
        self.assertLess(total_time, 5.0)  # All requests should complete within 5 seconds
        
        # All results should be dictionaries
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn('ride_counts', result)


class AnalyticsDataIntegrityTests(TestCase):
    """Test data integrity in analytics calculations"""
    
    def setUp(self):
        """Set up test data for integrity checks"""
        self.customer = User.objects.create_user(
            email='customer@integrity.test',
            username='customer_integrity',
            password='TestPass123!',
            phone_number='+250788777777',
            national_id='7777777777777777',
            first_name='Integrity',
            last_name='Customer',
            role='customer'
        )
    
    def test_revenue_calculation_accuracy(self):
        """Test that revenue calculations are accurate"""
        # Create rides with known values
        total_expected_revenue = Decimal('0.00')
        
        for i in range(3):
            fare = Decimal('2500.00') + (i * Decimal('500.00'))
            total_expected_revenue += fare
            
            Ride.objects.create(
                customer=self.customer,
                pickup_address=f'Test Pickup {i}',
                destination_address=f'Test Destination {i}',
                pickup_latitude=Decimal('-1.9441'),
                pickup_longitude=Decimal('30.0619'),
                destination_latitude=Decimal('-1.9706'),
                destination_longitude=Decimal('30.1044'),
                estimated_distance=Decimal('10.0'),
                estimated_duration=20,
                base_fare=Decimal('1000.00'),
                distance_fare=fare - Decimal('1000.00'),
                total_fare=fare,
                payment_method='cash',
                status='completed'
            )
        
        # Test analytics calculation
        end_date = date.today()
        start_date = end_date - timedelta(days=1)
        
        revenue_data = AnalyticsService.get_revenue_analysis(start_date, end_date)
        calculated_revenue = Decimal(str(revenue_data['summary']['total_revenue']))
        
        self.assertEqual(calculated_revenue, total_expected_revenue)
    
    def test_completion_rate_calculation(self):
        """Test ride completion rate calculation accuracy"""
        # Create 10 rides: 8 completed, 2 cancelled
        for i in range(10):
            status = 'completed' if i < 8 else 'cancelled_by_customer'
            
            Ride.objects.create(
                customer=self.customer,
                pickup_address=f'Test Pickup {i}',
                destination_address=f'Test Destination {i}',
                pickup_latitude=Decimal('-1.9441'),
                pickup_longitude=Decimal('30.0619'),
                destination_latitude=Decimal('-1.9706'),
                destination_longitude=Decimal('30.1044'),
                estimated_distance=Decimal('10.0'),
                estimated_duration=20,
                base_fare=Decimal('1000.00'),
                distance_fare=Decimal('1500.00'),
                total_fare=Decimal('2500.00'),
                payment_method='mtn_momo',
                status=status
            )
        
        # Test completion rate calculation
        end_date = date.today()
        start_date = end_date - timedelta(days=1)
        
        summary = AnalyticsService.get_ride_summary(start_date, end_date)
        completion_rate = summary['ride_counts']['completion_rate']
        
        expected_rate = (8 / 10) * 100  # 80%
        self.assertEqual(completion_rate, expected_rate)