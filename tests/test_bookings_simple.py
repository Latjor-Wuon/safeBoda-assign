"""
Simplified test for SafeBoda Rwanda booking system
Tests core booking functionality with actual model fields
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

from bookings.models import Ride
from authentication.models import DriverProfile

User = get_user_model()


class BasicBookingTests(TestCase):
    """Test basic booking functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.customer = User.objects.create_user(
            email='customer@booking.test',
            username='customer_booking',
            password='CustomerPass123!',
            phone_number='+250788111111',
            national_id='1111111111111111',
            first_name='Booking',
            last_name='Customer',
            role='customer'
        )
        
        self.driver = User.objects.create_user(
            email='driver@booking.test',
            username='driver_booking',
            password='DriverPass123!',
            phone_number='+250788222222',
            national_id='2222222222222222',
            first_name='Booking',
            last_name='Driver',
            role='driver'
        )
        
        # Create driver profile with all required fields
        self.driver_profile = DriverProfile.objects.create(
            user=self.driver,
            license_number='BOOK123456',
            license_expiry_date=date.today() + timedelta(days=365),
            license_category='B',
            vehicle_type='motorcycle',
            vehicle_make='Honda',
            vehicle_model='CB 125',
            vehicle_year=2023,
            vehicle_color='Blue',
            vehicle_plate_number='RAB 123H',
            insurance_number='INS123',
            insurance_expiry_date=date.today() + timedelta(days=365),
            vehicle_inspection_date=date.today(),
            vehicle_inspection_expiry=date.today() + timedelta(days=365),
            status='approved',
            is_online=True
        )
    
    def test_create_basic_ride(self):
        """Test creating a basic ride with required fields"""
        ride = Ride.objects.create(
            customer=self.customer,
            driver=self.driver,
            pickup_latitude=Decimal('-1.9441'),
            pickup_longitude=Decimal('30.0619'),
            pickup_address='Kigali City Market',
            destination_latitude=Decimal('-1.9706'),
            destination_longitude=Decimal('30.1044'),
            destination_address='Kigali Airport',
            estimated_distance=Decimal('15.5'),
            estimated_duration=30,
            base_fare=Decimal('1500.00'),
            distance_fare=Decimal('2000.00'),
            total_fare=Decimal('3500.00'),
            payment_method='mtn_momo',
            ride_type='boda',
            status='requested'
        )
        
        self.assertEqual(ride.customer, self.customer)
        self.assertEqual(ride.driver, self.driver)
        self.assertEqual(ride.status, 'requested')
        self.assertEqual(float(ride.total_fare), 3500.00)
        self.assertEqual(ride.payment_method, 'mtn_momo')
    
    def test_ride_without_driver(self):
        """Test creating a ride without assigned driver"""
        ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.9441'),
            pickup_longitude=Decimal('30.0619'),
            pickup_address='Nyabugogo',
            destination_latitude=Decimal('-1.9500'),
            destination_longitude=Decimal('30.0700'),
            destination_address='Kimisagara',
            estimated_distance=Decimal('5.0'),
            estimated_duration=15,
            base_fare=Decimal('1000.00'),
            distance_fare=Decimal('1000.00'),
            total_fare=Decimal('2000.00'),
            payment_method='cash',
            ride_type='boda',
            status='requested'
        )
        
        self.assertEqual(ride.customer, self.customer)
        self.assertIsNone(ride.driver)
        self.assertEqual(ride.status, 'requested')
        self.assertEqual(float(ride.estimated_distance), 5.0)
    
    def test_ride_status_progression(self):
        """Test ride status changes"""
        ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.9441'),
            pickup_longitude=Decimal('30.0619'),
            pickup_address='Kigali Heights',
            destination_latitude=Decimal('-1.9600'),
            destination_longitude=Decimal('30.0800'),
            destination_address='Kacyiru',
            estimated_distance=Decimal('8.0'),
            estimated_duration=20,
            base_fare=Decimal('1200.00'),
            distance_fare=Decimal('1500.00'),
            total_fare=Decimal('2700.00'),
            payment_method='airtel_money',
            ride_type='boda',
            status='requested'
        )
        
        # Test status progression
        self.assertEqual(ride.status, 'requested')
        
        # Assign driver
        ride.driver = self.driver
        ride.status = 'driver_assigned'
        ride.save()
        
        self.assertEqual(ride.status, 'driver_assigned')
        self.assertEqual(ride.driver, self.driver)
        
        # Start ride
        ride.status = 'in_progress'
        ride.save()
        
        self.assertEqual(ride.status, 'in_progress')
        
        # Complete ride
        ride.status = 'completed'
        ride.actual_distance = Decimal('7.8')
        ride.actual_duration = 18
        ride.save()
        
        self.assertEqual(ride.status, 'completed')
        self.assertEqual(float(ride.actual_distance), 7.8)
        self.assertEqual(ride.actual_duration, 18)
    
    def test_ride_cancellation(self):
        """Test ride cancellation"""
        ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.9300'),
            pickup_longitude=Decimal('30.0500'),
            pickup_address='Remera',
            destination_latitude=Decimal('-1.9400'),
            destination_longitude=Decimal('30.0600'),
            destination_address='Gisozi',
            estimated_distance=Decimal('3.5'),
            estimated_duration=10,
            base_fare=Decimal('800.00'),
            distance_fare=Decimal('700.00'),
            total_fare=Decimal('1500.00'),
            payment_method='cash',
            ride_type='boda',
            status='requested'
        )
        
        # Cancel by customer
        ride.status = 'cancelled_by_customer'
        ride.save()
        
        self.assertEqual(ride.status, 'cancelled_by_customer')
    
    def test_rwanda_location_fields(self):
        """Test Rwanda-specific location fields"""
        ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.9441'),
            pickup_longitude=Decimal('30.0619'),
            pickup_address='KN 5 Ave, Kigali',
            pickup_province='City of Kigali',
            pickup_district='Gasabo',
            pickup_sector='Kimironko',
            destination_latitude=Decimal('-1.9706'),
            destination_longitude=Decimal('30.1044'),
            destination_address='KIA Road, Airport',
            destination_province='City of Kigali',
            destination_district='Gasabo',
            destination_sector='Kanombe',
            estimated_distance=Decimal('12.0'),
            estimated_duration=25,
            base_fare=Decimal('1400.00'),
            distance_fare=Decimal('1800.00'),
            total_fare=Decimal('3200.00'),
            payment_method='mtn_momo',
            ride_type='boda'
        )
        
        self.assertEqual(ride.pickup_district, 'Gasabo')
        self.assertEqual(ride.pickup_sector, 'Kimironko')
        self.assertEqual(ride.destination_district, 'Gasabo')
        self.assertEqual(ride.destination_sector, 'Kanombe')
        self.assertEqual(ride.pickup_province, 'City of Kigali')
    
    def test_different_ride_types(self):
        """Test different ride types available"""
        # Motorcycle ride (boda)
        boda_ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.9441'),
            pickup_longitude=Decimal('30.0619'),
            pickup_address='Nyamirambo',
            destination_latitude=Decimal('-1.9500'),
            destination_longitude=Decimal('30.0700'),
            destination_address='Muhima',
            estimated_distance=Decimal('4.0'),
            estimated_duration=12,
            base_fare=Decimal('900.00'),
            distance_fare=Decimal('800.00'),
            total_fare=Decimal('1700.00'),
            payment_method='cash',
            ride_type='boda'
        )
        
        self.assertEqual(boda_ride.ride_type, 'boda')
        
        # Delivery ride
        delivery_ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.9300'),
            pickup_longitude=Decimal('30.0500'),
            pickup_address='Kisimenti',
            destination_latitude=Decimal('-1.9200'),
            destination_longitude=Decimal('30.0400'),
            destination_address='Kibagabaga',
            estimated_distance=Decimal('6.0'),
            estimated_duration=18,
            base_fare=Decimal('1100.00'),
            distance_fare=Decimal('1200.00'),
            total_fare=Decimal('2300.00'),
            payment_method='airtel_money',
            ride_type='delivery'
        )
        
        self.assertEqual(delivery_ride.ride_type, 'delivery')
    
    def test_payment_methods(self):
        """Test different payment methods"""
        payment_methods = ['cash', 'mtn_momo', 'airtel_money', 'card']
        
        for i, method in enumerate(payment_methods):
            ride = Ride.objects.create(
                customer=self.customer,
                pickup_latitude=Decimal(f'-1.94{i}0'),
                pickup_longitude=Decimal(f'30.06{i}0'),
                pickup_address=f'Location {i}',
                destination_latitude=Decimal(f'-1.95{i}0'),
                destination_longitude=Decimal(f'30.07{i}0'),
                destination_address=f'Destination {i}',
                estimated_distance=Decimal('5.0'),
                estimated_duration=15,
                base_fare=Decimal('1000.00'),
                distance_fare=Decimal('1000.00'),
                total_fare=Decimal('2000.00'),
                payment_method=method,
                ride_type='boda'
            )
            
            self.assertEqual(ride.payment_method, method)
    
    def test_surge_pricing(self):
        """Test surge pricing multiplier"""
        ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.9441'),
            pickup_longitude=Decimal('30.0619'),
            pickup_address='City Center',
            destination_latitude=Decimal('-1.9706'),
            destination_longitude=Decimal('30.1044'),
            destination_address='Airport',
            estimated_distance=Decimal('15.0'),
            estimated_duration=30,
            base_fare=Decimal('1500.00'),
            distance_fare=Decimal('2000.00'),
            surge_multiplier=Decimal('1.5'),  # 1.5x surge
            total_fare=Decimal('5250.00'),  # (1500 + 2000) * 1.5
            payment_method='mtn_momo',
            ride_type='boda'
        )
        
        self.assertEqual(float(ride.surge_multiplier), 1.5)
        self.assertEqual(float(ride.total_fare), 5250.00)
    
    def test_driver_profile_relationship(self):
        """Test driver profile relationship with rides"""
        ride = Ride.objects.create(
            customer=self.customer,
            driver=self.driver,
            pickup_latitude=Decimal('-1.9441'),
            pickup_longitude=Decimal('30.0619'),
            pickup_address='Test Pickup',
            destination_latitude=Decimal('-1.9506'),
            destination_longitude=Decimal('30.0719'),
            destination_address='Test Destination',
            estimated_distance=Decimal('5.0'),
            estimated_duration=15,
            base_fare=Decimal('1000.00'),
            distance_fare=Decimal('1000.00'),
            total_fare=Decimal('2000.00'),
            payment_method='cash',
            ride_type='boda'
        )
        
        # Check driver profile exists and is linked
        self.assertIsNotNone(ride.driver.driver_profile)
        self.assertEqual(ride.driver.driver_profile.license_number, 'BOOK123456')
        self.assertEqual(ride.driver.driver_profile.vehicle_make, 'Honda')
        self.assertTrue(ride.driver.driver_profile.is_online)


class BookingModelValidationTests(TestCase):
    """Test booking model validation and constraints"""
    
    def setUp(self):
        """Set up test user"""
        self.customer = User.objects.create_user(
            email='validation@booking.test',
            username='validation_customer',
            password='ValidationPass123!',
            phone_number='+250788333333',
            national_id='3333333333333333',
            first_name='Validation',
            last_name='Customer',
            role='customer'
        )
    
    def test_ride_model_string_representation(self):
        """Test ride __str__ method"""
        ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.9441'),
            pickup_longitude=Decimal('30.0619'),
            pickup_address='String Test Pickup',
            destination_latitude=Decimal('-1.9506'),
            destination_longitude=Decimal('30.0719'),
            destination_address='String Test Destination',
            estimated_distance=Decimal('5.0'),
            estimated_duration=15,
            base_fare=Decimal('1000.00'),
            distance_fare=Decimal('1000.00'),
            total_fare=Decimal('2000.00'),
            payment_method='cash',
            ride_type='boda'
        )
        
        # The string should contain customer info and ride details
        ride_str = str(ride)
        self.assertIn('Validation Customer', ride_str)
        self.assertIn('String Test Destination', ride_str)
    
    def test_decimal_field_precision(self):
        """Test decimal field precision for money and coordinates"""
        ride = Ride.objects.create(
            customer=self.customer,
            pickup_latitude=Decimal('-1.94411234'),  # High precision
            pickup_longitude=Decimal('30.06191234'),
            pickup_address='Precision Test',
            destination_latitude=Decimal('-1.95061234'),
            destination_longitude=Decimal('30.07191234'),
            destination_address='Precision Destination',
            estimated_distance=Decimal('5.12'),
            estimated_duration=15,
            base_fare=Decimal('1000.50'),
            distance_fare=Decimal('999.75'),
            total_fare=Decimal('2000.25'),
            payment_method='mtn_momo',
            ride_type='boda'
        )
        
        # Check precision is maintained
        self.assertEqual(float(ride.base_fare), 1000.50)
        self.assertEqual(float(ride.distance_fare), 999.75)
        self.assertEqual(float(ride.total_fare), 2000.25)
        self.assertEqual(float(ride.estimated_distance), 5.12)