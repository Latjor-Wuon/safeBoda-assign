"""
Testing utilities and fixtures for SafeBoda Rwanda
Provides common test data and helper functions
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
try:
    from authentication.models import DriverProfile, VerificationCode
except ImportError:
    DriverProfile = None
    VerificationCode = None

try:
    from bookings.models import Ride, RideLocation
except ImportError:
    Ride = None
    RideLocation = None

try:
    from payments.models import Payment, Transaction
except ImportError:
    Payment = None
    Transaction = None

try:
    from notifications.models import Notification, NotificationTemplate, NotificationPreference
except ImportError:
    Notification = None
    NotificationTemplate = None
    NotificationPreference = None

try:
    from government.models import RTDALicense, ComplianceReport
except ImportError:
    RTDALicense = None
    ComplianceReport = None

try:
    from analytics.models import RideAnalytics, DriverMetrics
except ImportError:
    RideAnalytics = None
    DriverMetrics = None

User = get_user_model()


class TestDataFactory:
    """
    Factory for creating test data with Rwanda-specific values
    """
    
    RWANDA_PROVINCES = ['Kigali', 'Northern', 'Southern', 'Eastern', 'Western']
    RWANDA_DISTRICTS = {
        'Kigali': ['Gasabo', 'Kicukiro', 'Nyarugenge'],
        'Northern': ['Rulindo', 'Gicumbi', 'Musanze', 'Burera', 'Gakenke'],
        'Southern': ['Nyanza', 'Gisagara', 'Nyaruguru', 'Huye', 'Nyamagabe', 'Ruhango', 'Muhanga', 'Kamonyi'],
        'Eastern': ['Rwamagana', 'Nyagatare', 'Gatsibo', 'Kayonza', 'Kirehe', 'Ngoma', 'Bugesera'],
        'Western': ['Rubavu', 'Nyabihu', 'Ngororero', 'Rusizi', 'Nyamasheke', 'Rutsiro', 'Karongi']
    }
    PHONE_PREFIXES = ['+250788', '+250789', '+250738', '+250739', '+250781', '+250782']
    
    @classmethod
    def create_test_user(cls, role='customer', **kwargs):
        """Create a test user with Rwanda-specific data"""
        defaults = {
            'username': f"testuser_{random.randint(1000, 9999)}",
            'email': f"test_{random.randint(1000, 9999)}@safeboda.rw",
            'first_name': random.choice(['Jean', 'Marie', 'Pierre', 'Claudine', 'Emmanuel', 'Jeanne']),
            'last_name': random.choice(['Uwimana', 'Mukamana', 'Niyonshuti', 'Uwimpuhwe', 'Hakizimana']),
            'phone_number': cls._generate_rwanda_phone(),
            'national_id': cls._generate_rwanda_national_id(),
            'role': role,
            'province': random.choice(cls.RWANDA_PROVINCES),
            'language_preference': random.choice(['en', 'fr', 'rw']),
            'is_active': True,
        }
        
        province = defaults['province']
        defaults['district'] = random.choice(cls.RWANDA_DISTRICTS[province])
        defaults['sector'] = f"Sector_{random.randint(1, 5)}"
        defaults['cell'] = f"Cell_{random.randint(1, 10)}"
        defaults['village'] = f"Village_{random.randint(1, 20)}"
        
        defaults.update(kwargs)
        
        user = User.objects.create_user(
            password='testpass123',
            **defaults
        )
        
        # Create notification preferences
        NotificationPreference.objects.get_or_create(user=user)
        
        return user
    
    @classmethod
    def create_test_driver(cls, **kwargs):
        """Create a test driver with profile"""
        user = cls.create_test_user(role='driver', **kwargs)
        
        # Create driver profile
        profile = DriverProfile.objects.create(
            user=user,
            license_number=f"RW{random.randint(100000000, 999999999)}",
            license_expiry_date=timezone.now().date() + timedelta(days=365),
            vehicle_type=random.choice(['motorcycle', 'bicycle']),
            vehicle_registration=f"RAD{random.randint(100, 999)}T",
            is_verified=True,
            is_active=True,
            rating=Decimal(str(round(random.uniform(4.0, 5.0), 1))),
        )
        
        # Create RTDA license
        RTDALicense.objects.create(
            driver=user,
            license_number=profile.license_number,
            issue_date=timezone.now().date() - timedelta(days=30),
            expiry_date=profile.license_expiry_date,
            license_category=profile.vehicle_type,
            status='active',
        )
        
        return user
    
    @classmethod
    def create_test_ride(cls, customer=None, driver=None, **kwargs):
        """Create a test ride"""
        if not customer:
            customer = cls.create_test_user(role='customer')
        if not driver:
            driver = cls.create_test_driver()
        
        defaults = {
            'customer': customer,
            'driver': driver,
            'pickup_address': "KG 11 Ave, Kigali",
            'pickup_latitude': Decimal('-1.9441') + Decimal(str(random.uniform(-0.1, 0.1))),
            'pickup_longitude': Decimal('30.0619') + Decimal(str(random.uniform(-0.1, 0.1))),
            'destination_address': "KN 3 Rd, Kigali",
            'destination_latitude': Decimal('-1.9506') + Decimal(str(random.uniform(-0.1, 0.1))),
            'destination_longitude': Decimal('30.0588') + Decimal(str(random.uniform(-0.1, 0.1))),
            'ride_type': random.choice(['standard', 'express', 'shared']),
            'payment_method': random.choice(['mtn_momo', 'airtel_money', 'cash']),
            'base_fare': Decimal(str(random.randint(500, 2000))),
            'distance_km': Decimal(str(round(random.uniform(1.0, 15.0), 2))),
            'estimated_duration': random.randint(10, 45),
            'status': random.choice(['requested', 'accepted', 'in_progress', 'completed']),
        }
        defaults.update(kwargs)
        
        ride = Ride.objects.create(**defaults)
        
        # Create ride locations for tracking
        for i in range(random.randint(5, 15)):
            RideLocation.objects.create(
                ride=ride,
                latitude=ride.pickup_latitude + Decimal(str(random.uniform(-0.01, 0.01))),
                longitude=ride.pickup_longitude + Decimal(str(random.uniform(-0.01, 0.01))),
                timestamp=timezone.now() - timedelta(minutes=random.randint(1, 30)),
            )
        
        return ride
    
    @classmethod
    def create_test_payment(cls, ride=None, **kwargs):
        """Create a test payment"""
        if not ride:
            ride = cls.create_test_ride()
        
        defaults = {
            'ride': ride,
            'amount': ride.base_fare,
            'payment_method': ride.payment_method,
            'status': random.choice(['pending', 'completed', 'failed']),
            'provider_reference': f"TXN{random.randint(100000, 999999)}",
            'phone_number': ride.customer.phone_number,
        }
        defaults.update(kwargs)
        
        payment = Payment.objects.create(**defaults)
        
        # Create transaction record
        Transaction.objects.create(
            payment=payment,
            transaction_type='payment',
            amount=payment.amount,
            status=payment.status,
            reference_id=payment.provider_reference,
            provider_response={'status': 'success', 'message': 'Payment processed'},
        )
        
        return payment
    
    @classmethod
    def create_test_notification(cls, user=None, **kwargs):
        """Create a test notification"""
        if not user:
            user = cls.create_test_user()
        
        # Create notification template if it doesn't exist
        template, created = NotificationTemplate.objects.get_or_create(
            name='test_template',
            defaults={
                'notification_type': 'general',
                'subject': 'Test Notification',
                'message': 'This is a test notification for {{user_name}}',
                'language': 'en',
            }
        )
        
        defaults = {
            'user': user,
            'template': template,
            'title': 'Test Notification',
            'message': f'Test message for {user.get_full_name()}',
            'notification_type': 'general',
            'channel': random.choice(['sms', 'email', 'push']),
            'status': random.choice(['pending', 'sent', 'delivered', 'read']),
        }
        defaults.update(kwargs)
        
        return Notification.objects.create(**defaults)
    
    @classmethod
    def _generate_rwanda_phone(cls):
        """Generate a valid Rwanda phone number"""
        prefix = random.choice(cls.PHONE_PREFIXES)
        suffix = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return f"{prefix}{suffix}"
    
    @classmethod
    def _generate_rwanda_national_id(cls):
        """Generate a valid Rwanda National ID format"""
        year = random.randint(1980, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        sequence = random.randint(10000, 99999)
        gender = random.randint(1, 2)  # 1 for male, 2 for female
        checksum = random.randint(10, 99)
        
        return f"{year:04d}{month:02d}{day:02d}{sequence:05d}{gender:01d}{checksum:02d}"
    
    @classmethod
    def create_bulk_test_data(cls, users=50, rides=100, payments=80):
        """Create bulk test data for performance testing"""
        print(f"Creating {users} test users...")
        customers = [cls.create_test_user(role='customer') for _ in range(users // 2)]
        drivers = [cls.create_test_driver() for _ in range(users // 2)]
        
        print(f"Creating {rides} test rides...")
        test_rides = []
        for _ in range(rides):
            customer = random.choice(customers)
            driver = random.choice(drivers)
            ride = cls.create_test_ride(customer=customer, driver=driver)
            test_rides.append(ride)
        
        print(f"Creating {payments} test payments...")
        for _ in range(payments):
            ride = random.choice(test_rides)
            cls.create_test_payment(ride=ride)
        
        print("Creating analytics data...")
        for driver in drivers:
            DriverMetrics.objects.create(
                driver=driver,
                total_rides=random.randint(10, 100),
                completed_rides=random.randint(8, 95),
                cancelled_rides=random.randint(0, 5),
                total_earnings=Decimal(str(random.randint(50000, 500000))),
                average_rating=Decimal(str(round(random.uniform(4.0, 5.0), 2))),
                acceptance_rate=Decimal(str(round(random.uniform(80.0, 100.0), 2))),
            )
        
        return {
            'customers': customers,
            'drivers': drivers,
            'rides': test_rides,
        }


class TestAssertions:
    """
    Custom assertions for Rwanda-specific validations
    """
    
    @staticmethod
    def assert_valid_rwanda_phone(phone_number):
        """Assert that phone number is valid for Rwanda"""
        assert phone_number.startswith('+250'), f"Phone number {phone_number} should start with +250"
        assert len(phone_number) == 13, f"Phone number {phone_number} should be 13 characters long"
        assert phone_number[4:7] in ['788', '789', '738', '739', '781', '782'], \
            f"Phone number {phone_number} has invalid operator code"
    
    @staticmethod
    def assert_valid_rwanda_national_id(national_id):
        """Assert that National ID is valid for Rwanda"""
        assert len(national_id) == 16, f"National ID {national_id} should be 16 digits long"
        assert national_id.isdigit(), f"National ID {national_id} should contain only digits"
        
        year = int(national_id[:4])
        assert 1900 <= year <= 2100, f"Invalid birth year {year} in National ID"
        
        month = int(national_id[4:6])
        assert 1 <= month <= 12, f"Invalid birth month {month} in National ID"
        
        day = int(national_id[6:8])
        assert 1 <= day <= 31, f"Invalid birth day {day} in National ID"
    
    @staticmethod
    def assert_valid_rwanda_location(province, district):
        """Assert that location is valid for Rwanda"""
        valid_districts = TestDataFactory.RWANDA_DISTRICTS
        assert province in valid_districts, f"Invalid province {province}"
        assert district in valid_districts[province], \
            f"District {district} not found in province {province}"
    
    @staticmethod
    def assert_performance_metrics(response_time, error_rate, throughput):
        """Assert performance metrics meet Rwanda deployment standards"""
        assert response_time <= 2000, f"Response time {response_time}ms exceeds 2s limit"
        assert error_rate <= 1.0, f"Error rate {error_rate}% exceeds 1% limit"
        assert throughput >= 100, f"Throughput {throughput} req/s below 100 req/s minimum"