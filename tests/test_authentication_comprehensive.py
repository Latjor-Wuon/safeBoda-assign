"""
Comprehensive unit tests for SafeBoda Rwanda authentication system
Achieving 90%+ code coverage for RTDA compliance
"""


from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import DriverProfile, VerificationCode
from authentication.serializers import (
    UserRegistrationSerializer, UserLoginSerializer, 
    UserProfileSerializer, DriverProfileSerializer
)
from authentication.permissions import IsOwnerOrReadOnly, IsDriverOrReadOnly
from testing_framework.utils import TestDataFactory, TestAssertions

User = get_user_model()


class UserModelTests(TestCase):
    """
    Unit tests for User model and Rwanda-specific validations
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
    
    def test_create_user_with_valid_data(self):
        """Test creating user with valid Rwanda data"""
        user_data = {
            'username': 'testuser',
            'email': 'test@safeboda.rw',
            'password': 'testpass123',
            'first_name': 'Jean',
            'last_name': 'Uwimana',
            'phone_number': '+250788123456',
            'national_id': '1199712345678901',
            'role': 'customer',
            'province': 'Kigali',
            'district': 'Gasabo',
        }
        
        user = User.objects.create_user(**user_data)
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@safeboda.rw')
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(user.role, 'customer')
        self.assertEqual(user.province, 'Kigali')
        self.assertEqual(user.district, 'Gasabo')
        TestAssertions.assert_valid_rwanda_phone(user.phone_number)
        TestAssertions.assert_valid_rwanda_national_id(user.national_id)
    
    def test_create_superuser(self):
        """Test creating superuser with admin role"""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@safeboda.rw',
            password='adminpass123',
        )
        
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
        self.assertEqual(superuser.role, 'admin')
    
    def test_user_string_representation(self):
        """Test user __str__ method"""
        user = self.test_factory.create_test_user(
            username='testuser',
            email='test@safeboda.rw'
        )
        
        self.assertEqual(str(user), 'test@safeboda.rw')
    
    def test_get_full_name(self):
        """Test get_full_name method"""
        user = self.test_factory.create_test_user(
            first_name='Jean',
            last_name='Uwimana'
        )
        
        self.assertEqual(user.get_full_name(), 'Jean Uwimana')
    
    def test_get_short_name(self):
        """Test get_short_name method"""
        user = self.test_factory.create_test_user(first_name='Jean')
        
        self.assertEqual(user.get_short_name(), 'Jean')
    
    def test_phone_number_uniqueness(self):
        """Test phone number uniqueness constraint"""
        phone = '+250788123456'
        self.test_factory.create_test_user(phone_number=phone)
        
        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            self.test_factory.create_test_user(phone_number=phone)
    
    def test_email_uniqueness(self):
        """Test email uniqueness constraint"""
        email = 'test@safeboda.rw'
        self.test_factory.create_test_user(email=email)
        
        with self.assertRaises(Exception):  # IntegrityError
            self.test_factory.create_test_user(email=email)
    
    def test_invalid_phone_number(self):
        """Test validation of invalid phone numbers"""
        invalid_phones = [
            '+25078812345',    # Too short
            '+2507881234567',  # Too long
            '0788123456',      # Missing country code
            '+254788123456',   # Wrong country code
        ]
        
        for phone in invalid_phones:
            with self.assertRaises((ValidationError, ValueError)):
                user = User(
                    username='test',
                    email='test@test.com',
                    phone_number=phone
                )
                user.full_clean()
    
    def test_rwanda_location_validation(self):
        """Test Rwanda location hierarchy validation"""
        # Valid location
        user = self.test_factory.create_test_user(
            province='Kigali',
            district='Gasabo'
        )
        TestAssertions.assert_valid_rwanda_location(user.province, user.district)
        
        # Invalid province should raise error
        with self.assertRaises(AssertionError):
            TestAssertions.assert_valid_rwanda_location('InvalidProvince', 'Gasabo')
    
    def test_user_age_calculation(self):
        """Test age calculation from date of birth"""
        birth_date = datetime(1995, 5, 15).date()
        user = self.test_factory.create_test_user(date_of_birth=birth_date)
        
        age = user.age
        expected_age = (datetime.now().date() - birth_date).days // 365
        
        self.assertAlmostEqual(age, expected_age, delta=1)


class DriverProfileModelTests(TestCase):
    """
    Unit tests for DriverProfile model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver_user = self.test_factory.create_test_driver()
    
    def test_create_driver_profile(self):
        """Test creating driver profile"""
        profile = DriverProfile.objects.get(user=self.driver_user)
        
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user, self.driver_user)
        self.assertTrue(profile.license_number.startswith('RW'))
        self.assertIsNotNone(profile.license_expiry_date)
        self.assertIn(profile.vehicle_type, ['motorcycle', 'bicycle'])
    
    def test_driver_profile_string_representation(self):
        """Test driver profile __str__ method"""
        profile = DriverProfile.objects.get(user=self.driver_user)
        expected_str = f"{self.driver_user.get_full_name()} - {profile.license_number}"
        
        self.assertEqual(str(profile), expected_str)
    
    def test_driver_rating_validation(self):
        """Test driver rating validation (1.0-5.0)"""
        profile = DriverProfile.objects.get(user=self.driver_user)
        
        # Valid ratings
        valid_ratings = [Decimal('1.0'), Decimal('3.5'), Decimal('5.0')]
        for rating in valid_ratings:
            profile.rating = rating
            profile.full_clean()  # Should not raise
        
        # Invalid ratings
        invalid_ratings = [Decimal('0.5'), Decimal('5.5'), Decimal('-1.0')]
        for rating in invalid_ratings:
            profile.rating = rating
            with self.assertRaises(ValidationError):
                profile.full_clean()
    
    def test_license_expiry_validation(self):
        """Test license expiry date validation"""
        profile = DriverProfile.objects.get(user=self.driver_user)
        
        # Future date (valid)
        future_date = timezone.now().date() + timedelta(days=365)
        profile.license_expiry_date = future_date
        profile.full_clean()  # Should not raise
        
        # Past date (should be handled by business logic)
        past_date = timezone.now().date() - timedelta(days=30)
        profile.license_expiry_date = past_date
        profile.full_clean()  # Model allows, business logic handles
    
    def test_vehicle_registration_format(self):
        """Test vehicle registration number format"""
        profile = DriverProfile.objects.get(user=self.driver_user)
        
        # Should follow Rwanda format (RAD123T, etc.)
        self.assertRegex(profile.vehicle_registration, r'^RAD\d{3}[A-Z]$')


class VerificationCodeModelTests(TestCase):
    """
    Unit tests for VerificationCode model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.user = self.test_factory.create_test_user()
    
    def test_create_verification_code(self):
        """Test creating verification code"""
        code = VerificationCode.objects.create(
            user=self.user,
            verification_type='email',
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        self.assertEqual(code.user, self.user)
        self.assertEqual(code.verification_type, 'email')
        self.assertEqual(code.code, '123456')
        self.assertFalse(code.is_used)
        self.assertIsNone(code.used_at)
    
    def test_verification_code_expiry(self):
        """Test verification code expiry logic"""
        # Create expired code
        expired_code = VerificationCode.objects.create(
            user=self.user,
            verification_type='phone',
            code='654321',
            expires_at=timezone.now() - timedelta(minutes=5)
        )
        
        self.assertTrue(expired_code.expires_at < timezone.now())
        
        # Create valid code
        valid_code = VerificationCode.objects.create(
            user=self.user,
            verification_type='email',
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        self.assertTrue(valid_code.expires_at > timezone.now())
    
    def test_verification_code_usage(self):
        """Test marking verification code as used"""
        code = VerificationCode.objects.create(
            user=self.user,
            verification_type='email',
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Mark as used
        code.is_used = True
        code.used_at = timezone.now()
        code.save()
        
        code.refresh_from_db()
        self.assertTrue(code.is_used)
        self.assertIsNotNone(code.used_at)
    
    def test_verification_code_string_representation(self):
        """Test verification code __str__ method"""
        code = VerificationCode.objects.create(
            user=self.user,
            verification_type='email',
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        expected_str = f"{self.user.email} - email - 123456"
        self.assertEqual(str(code), expected_str)


class AuthenticationSerializerTests(TestCase):
    """
    Unit tests for authentication serializers
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
    
    def test_user_registration_serializer_valid_data(self):
        """Test user registration serializer with valid data"""
        valid_data = {
            'username': 'newuser',
            'email': 'newuser@safeboda.rw',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
            'first_name': 'Jean',
            'last_name': 'Uwimana',
            'phone_number': '+250788123456',
            'national_id': '1199712345678901',
            'role': 'customer',
            'province': 'Kigali',
            'district': 'Gasabo',
            'language_preference': 'en',
        }
        
        serializer = UserRegistrationSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        user = serializer.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.role, 'customer')
        TestAssertions.assert_valid_rwanda_phone(user.phone_number)
    
    def test_user_registration_serializer_password_mismatch(self):
        """Test registration serializer with password mismatch"""
        invalid_data = {
            'username': 'newuser',
            'email': 'newuser@safeboda.rw',
            'password': 'StrongPassword123!',
            'password_confirm': 'DifferentPassword123!',
            'phone_number': '+250788123456',
        }
        
        serializer = UserRegistrationSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password_confirm', serializer.errors)
    
    def test_user_registration_serializer_invalid_phone(self):
        """Test registration serializer with invalid phone"""
        invalid_data = {
            'username': 'newuser',
            'email': 'newuser@safeboda.rw',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
            'phone_number': '0788123456',  # Missing +250
        }
        
        serializer = UserRegistrationSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)
    
    def test_user_login_serializer(self):
        """Test user login serializer"""
        user = self.test_factory.create_test_user(
            email='test@safeboda.rw',
            password='testpass123'
        )
        
        login_data = {
            'email': 'test@safeboda.rw',
            'password': 'testpass123',
        }
        
        serializer = UserLoginSerializer(data=login_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        validated_data = serializer.validated_data
        self.assertEqual(validated_data['user'], user)
    
    def test_user_profile_serializer(self):
        """Test user profile serializer"""
        user = self.test_factory.create_test_user()
        
        serializer = UserProfileSerializer(user)
        data = serializer.data
        
        self.assertEqual(data['email'], user.email)
        self.assertEqual(data['first_name'], user.first_name)
        self.assertEqual(data['role'], user.role)
        self.assertIn('full_name', data)
        self.assertIn('get_rwanda_address', data)
    
    def test_driver_profile_serializer(self):
        """Test driver profile serializer"""
        driver = self.test_factory.create_test_driver()
        profile = DriverProfile.objects.get(user=driver)
        
        serializer = DriverProfileSerializer(profile)
        data = serializer.data
        
        self.assertEqual(data['user'], driver.id)
        self.assertIn('license_number', data)
        self.assertIn('vehicle_type', data)
        self.assertIn('rating', data)


class AuthenticationPermissionTests(TestCase):
    """
    Unit tests for authentication permissions
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.user = self.test_factory.create_test_user()
        self.other_user = self.test_factory.create_test_user()
        
    def test_is_owner_or_read_only_permission(self):
        """Test IsOwnerOrReadOnly permission"""
        permission = IsOwnerOrReadOnly()
        
        # Mock request and view
        class MockRequest:
            def __init__(self, user, method):
                self.user = user
                self.method = method
        
        class MockView:
            pass
        
        class MockObject:
            def __init__(self, user):
                self.user = user
        
        view = MockView()
        obj = MockObject(self.user)
        
        # Owner should have all permissions
        request = MockRequest(self.user, 'PUT')
        self.assertTrue(permission.has_object_permission(request, view, obj))
        
        # Other user should only have read permissions
        request = MockRequest(self.other_user, 'GET')
        self.assertTrue(permission.has_object_permission(request, view, obj))
        
        request = MockRequest(self.other_user, 'PUT')
        self.assertFalse(permission.has_object_permission(request, view, obj))
    
    def test_is_driver_or_read_only_permission(self):
        """Test IsDriverOrReadOnly permission"""
        permission = IsDriverOrReadOnly()
        
        driver = self.test_factory.create_test_driver()
        customer = self.test_factory.create_test_user(role='customer')
        
        class MockRequest:
            def __init__(self, user, method):
                self.user = user
                self.method = method
        
        class MockView:
            pass
        
        view = MockView()
        
        # Driver should have write permissions
        request = MockRequest(driver, 'POST')
        self.assertTrue(permission.has_permission(request, view))
        
        # Customer should only have read permissions for safe methods
        request = MockRequest(customer, 'GET')
        self.assertTrue(permission.has_permission(request, view))
        
        request = MockRequest(customer, 'POST')
        self.assertFalse(permission.has_permission(request, view))
