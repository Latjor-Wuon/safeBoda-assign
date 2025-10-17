"""
Test user management and authentication functionality for SafeBoda Rwanda
Comprehensive testing of JWT authentication, user registration, profiles
"""
import json
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock

from authentication.models import DriverProfile
# Note: CustomerProfile and AdminProfile are not implemented in the current system
# They would need to be added to authentication/models.py for full functionality

User = get_user_model()


class UserModelTests(TestCase):
    """Test custom user model functionality"""
    
    def test_create_customer_user(self):
        """Test creating a customer user"""
        user = User.objects.create_user(
            email='customer@usermodel.test',
            username='customer_test',
            password='CustomerPass123!',
            phone_number='+250788111111',
            national_id='1111111111111111',
            first_name='Test',
            last_name='Customer',
            role='customer'
        )
        
        self.assertEqual(user.email, 'customer@usermodel.test')
        self.assertEqual(user.username, 'customer_test')
        self.assertEqual(user.role, 'customer')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('CustomerPass123!'))
    
    def test_create_driver_user(self):
        """Test creating a driver user"""
        user = User.objects.create_user(
            email='driver@usermodel.test',
            username='driver_test',
            password='DriverPass123!',
            phone_number='+250788222222',
            national_id='2222222222222222',
            first_name='Test',
            last_name='Driver',
            role='driver'
        )
        
        self.assertEqual(user.role, 'driver')
        self.assertTrue(user.is_active)
    
    def test_create_admin_user(self):
        """Test creating an admin user"""
        user = User.objects.create_user(
            email='admin@usermodel.test',
            username='admin_test',
            password='AdminPass123!',
            phone_number='+250788333333',
            national_id='3333333333333333',
            first_name='Test',
            last_name='Admin',
            role='admin',
            is_staff=True
        )
        
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.is_staff)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email='super@usermodel.test',
            username='superuser_test',
            password='SuperPass123!',
            phone_number='+250788444444',
            national_id='4444444444444444',
            first_name='Super',
            last_name='User'
        )
        
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        # Note: The current User model defaults role to 'customer', 
        # but superuser should probably be 'admin'
    
    def test_user_string_representation(self):
        """Test user __str__ method"""
        user = User.objects.create_user(
            email='string@usermodel.test',
            username='string_test',
            password='StringPass123!',
            phone_number='+250788555555',
            national_id='5555555555555555',
            first_name='String',
            last_name='User'
        )
        
        # The actual __str__ method returns "First Last (email)"
        self.assertEqual(str(user), 'String User (string@usermodel.test)')
    
    def test_user_full_name_property(self):
        """Test user full_name property"""
        user = User.objects.create_user(
            email='name@usermodel.test',
            username='name_test',
            password='NamePass123!',
            phone_number='+250788666666',
            national_id='6666666666666666',
            first_name='John',
            last_name='Doe'
        )
        
        self.assertEqual(user.full_name, 'John Doe')
    
    def test_unique_email_constraint(self):
        """Test that email must be unique"""
        User.objects.create_user(
            email='unique@usermodel.test',
            username='unique_test1',
            password='UniquePass123!',
            phone_number='+250788777777',
            national_id='7777777777777777'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='unique@usermodel.test',  # Duplicate email
                username='unique_test2',
                password='UniquePass123!',
                phone_number='+250788888888',
                national_id='8888888888888888'
            )
    
    def test_unique_phone_constraint(self):
        """Test that phone number must be unique"""
        User.objects.create_user(
            email='phone1@usermodel.test',
            username='phone_test1',
            password='PhonePass123!',
            phone_number='+250788999999',
            national_id='9999999999999999'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='phone2@usermodel.test',
                username='phone_test2',
                password='PhonePass123!',
                phone_number='+250788999999',  # Duplicate phone
                national_id='1010101010101010'
            )


class ProfileModelTests(TestCase):
    """Test user profile models"""
    
    def setUp(self):
        """Set up test users"""
        self.driver = User.objects.create_user(
            email='driver@profiles.test',
            username='driver_profile',
            password='DriverPass123!',
            phone_number='+250788222222',
            national_id='2222222222222222',
            first_name='Profile',
            last_name='Driver',
            role='driver'
        )
    
    def test_driver_profile_creation(self):
        """Test creating a driver profile"""
        profile = DriverProfile.objects.create(
            user=self.driver,
            license_number='ABC123456',
            license_expiry_date=date.today() + timedelta(days=365),
            license_category='B',
            vehicle_type='motorcycle',
            vehicle_plate_number='RAB 123A',
            vehicle_make='Honda',
            vehicle_model='CB 150',
            vehicle_year=2020,
            vehicle_color='Blue',
            insurance_number='INS987654321',
            insurance_expiry_date=date.today() + timedelta(days=365),
            vehicle_inspection_date=date.today() - timedelta(days=30),
            vehicle_inspection_expiry=date.today() + timedelta(days=335)
        )
        
        self.assertEqual(profile.user, self.driver)
        self.assertEqual(profile.license_number, 'ABC123456')
        self.assertEqual(profile.vehicle_type, 'motorcycle')
        self.assertEqual(profile.vehicle_make, 'Honda')
        self.assertEqual(profile.status, 'pending')
    
    def test_driver_profile_basic_fields(self):
        """Test driver profile basic field storage"""
        profile = DriverProfile.objects.create(
            user=self.driver,
            license_number='ABC123456',
            license_expiry_date=date.today() + timedelta(days=365),
            vehicle_type='motorcycle',
            vehicle_make='Yamaha',
            vehicle_model='FZ-S',
            vehicle_year=2021,
            vehicle_color='Black',
            vehicle_plate_number='RAB 456B',
            insurance_number='INS123',
            insurance_expiry_date=date.today() + timedelta(days=365),
            vehicle_inspection_date=date.today(),
            vehicle_inspection_expiry=date.today() + timedelta(days=365)
        )
        
        self.assertEqual(profile.vehicle_make, 'Yamaha')
        self.assertEqual(profile.vehicle_model, 'FZ-S')
        self.assertEqual(profile.vehicle_year, 2021)
        self.assertEqual(profile.vehicle_color, 'Black')
        self.assertEqual(profile.vehicle_plate_number, 'RAB 456B')
    
    def test_driver_profile_license_expiry_check(self):
        """Test checking if driver license is expired"""
        # Create profile with expired license
        expired_profile = DriverProfile.objects.create(
            user=self.driver,
            license_number='ABC123456',
            license_expiry_date=date.today() - timedelta(days=30),  # Expired
            license_category='B',
            vehicle_type='motorcycle',
            vehicle_plate_number='RAB 789C',
            vehicle_make='Honda',
            vehicle_model='CB150',
            vehicle_year=2020,
            vehicle_color='Blue',
            insurance_number='INS123',
            insurance_expiry_date=date.today() + timedelta(days=365),
            vehicle_inspection_date=date.today(),
            vehicle_inspection_expiry=date.today() + timedelta(days=365)
        )
        
        # Check if license is expired by comparing dates
        is_expired = expired_profile.license_expiry_date < date.today()
        self.assertTrue(is_expired)


class AuthenticationBasicTests(TestCase):
    """Test basic authentication functionality"""
    
    def test_user_model_basic_functionality(self):
        """Test basic User model functionality"""
        user = User.objects.create_user(
            email='basic@test.com',
            username='basic_test',
            password='BasicPass123!',
            first_name='Basic',
            last_name='Test',
            phone_number='+250788111111',
            national_id='1111111111111111',
            role='customer'
        )
        
        self.assertEqual(user.email, 'basic@test.com')
        self.assertEqual(user.role, 'customer')
        self.assertTrue(user.check_password('BasicPass123!'))
        self.assertEqual(user.full_name, 'Basic Test')
    
    def test_driver_profile_creation_with_user(self):
        """Test creating driver profile linked to user"""
        driver_user = User.objects.create_user(
            email='driver@basic.test',
            username='driver_basic',
            password='DriverPass123!',
            first_name='Driver',
            last_name='Basic',
            phone_number='+250788222222',
            national_id='2222222222222222',
            role='driver'
        )
        
        profile = DriverProfile.objects.create(
            user=driver_user,
            license_number='ABC123456',
            license_expiry_date=date.today() + timedelta(days=365),
            license_category='B',
            vehicle_type='motorcycle',
            vehicle_make='Honda',
            vehicle_model='CB 150',
            vehicle_year=2020,
            vehicle_plate_number='RAB 123D',
            insurance_number='INS123',
            insurance_expiry_date=date.today() + timedelta(days=365),
            vehicle_inspection_date=date.today(),
            vehicle_inspection_expiry=date.today() + timedelta(days=365)
        )
        
        self.assertEqual(profile.user, driver_user)
        self.assertEqual(profile.license_number, 'ABC123456')
        self.assertEqual(profile.vehicle_make, 'Honda')


class AuthenticationIntegrationTests(TestCase):
    """Test authentication integration with JWT"""
    
    def setUp(self):
        """Set up test users"""
        self.customer = User.objects.create_user(
            email='customer@auth.test',
            username='customer_auth',
            password='CustomerPass123!',
            phone_number='+250788111111',
            national_id='1111111111111111',
            first_name='Auth',
            last_name='Customer',
            role='customer'
        )
        
        self.driver = User.objects.create_user(
            email='driver@auth.test',
            username='driver_auth',
            password='DriverPass123!',
            phone_number='+250788222222',
            national_id='2222222222222222',
            first_name='Auth',
            last_name='Driver',
            role='driver'
        )
    
    def test_jwt_token_generation(self):
        """Test JWT token generation for users"""
        # Generate token for customer
        refresh = RefreshToken.for_user(self.customer)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)
        self.assertTrue(len(access_token) > 50)  # JWT tokens are long
        
        # Verify token contains user data
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        
        try:
            UntypedToken(access_token)  # This should not raise an exception
            token_valid = True
        except (InvalidToken, TokenError):
            token_valid = False
            
        self.assertTrue(token_valid)
    
    def test_driver_with_profile_relationship(self):
        """Test driver user with profile relationship"""
        # Create driver profile
        profile = DriverProfile.objects.create(
            user=self.driver,
            license_number='ABC123456',
            license_expiry_date=date.today() + timedelta(days=365),
            license_category='B',
            vehicle_type='motorcycle',
            vehicle_make='Honda',
            vehicle_model='CB 150',
            vehicle_year=2020,
            vehicle_plate_number='RAB 123F',
            insurance_number='INS123',
            insurance_expiry_date=date.today() + timedelta(days=365),
            vehicle_inspection_date=date.today(),
            vehicle_inspection_expiry=date.today() + timedelta(days=365)
        )
        
        # Test relationship
        self.assertEqual(profile.user, self.driver)
        self.assertEqual(self.driver.driver_profile, profile)
        
        # Test profile string representation
        expected_str = f"Driver: {self.driver.full_name} - {profile.vehicle_plate_number}"
        self.assertEqual(str(profile), expected_str)
    
    def test_user_address_formatting(self):
        """Test Rwanda address formatting"""
        user = User.objects.create_user(
            email='address@test.com',
            username='address_test',
            password='AddressPass123!',
            phone_number='+250788999999',
            national_id='9999999999999999',
            first_name='Address',
            last_name='Test',
            province='Kigali City',
            district='Gasabo',
            sector='Kimironko',
            cell='Kibagabaga',
            village='Nyarutarama'
        )
        
        expected_address = "Nyarutarama, Kibagabaga, Kimironko, Gasabo, Kigali City"
        self.assertEqual(user.get_rwanda_address(), expected_address)
        
        # Test partial address
        user.village = ''
        user.cell = ''
        expected_partial = "Kimironko, Gasabo, Kigali City"
        self.assertEqual(user.get_rwanda_address(), expected_partial)