"""
Unit tests for SafeBoda Rwanda authentication system
Tests user registration, login, JWT tokens, and role-based permissions
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.exceptions import ValidationError
from unittest.mock import patch, Mock
import uuid

from authentication.models import User, DriverProfile, VerificationCode
from authentication.serializers import UserRegistrationSerializer, UserLoginSerializer
from authentication.views import UserRegistrationView
from tests import TEST_USER_DATA, TEST_DRIVER_DATA

User = get_user_model()


class UserModelTests(TestCase):
    """
    Test cases for User model functionality
    """
    
    def setUp(self):
        """Set up test data"""
        self.user_data = TEST_USER_DATA.copy()
    
    def test_create_user_success(self):
        """Test creating a user with valid data"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.username, self.user_data['username'])
        self.assertEqual(user.phone_number, self.user_data['phone_number'])
        self.assertEqual(user.national_id, self.user_data['national_id'])
        self.assertEqual(user.role, 'customer')
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertIsNotNone(user.id)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_superuser_success(self):
        """Test creating a superuser"""
        superuser = User.objects.create_superuser(
            email='admin@safeboda.rw',
            username='admin',
            password='AdminPassword123!',
            phone_number='+250788999999',
            national_id='9999999999999999'
        )
        
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertEqual(superuser.role, 'admin')
    
    def test_user_string_representation(self):
        """Test user __str__ method"""
        user = User.objects.create_user(**self.user_data)
        expected_str = f"{user.first_name} {user.last_name} ({user.email})"
        self.assertEqual(str(user), expected_str)
    
    def test_get_full_name(self):
        """Test get_full_name method"""
        user = User.objects.create_user(**self.user_data)
        expected_name = f"{user.first_name} {user.last_name}"
        self.assertEqual(user.get_full_name(), expected_name)
    
    def test_national_id_validation(self):
        """Test Rwanda National ID validation"""
        # Test valid 16-digit ID
        user_data = self.user_data.copy()
        user_data['national_id'] = '1234567890123456'
        user = User.objects.create_user(**user_data)
        self.assertEqual(user.national_id, '1234567890123456')
        
        # Test invalid ID length
        user_data['national_id'] = '12345'
        with self.assertRaises(ValidationError):
            user = User(**user_data)
            user.full_clean()
    
    def test_phone_number_uniqueness(self):
        """Test phone number uniqueness constraint"""
        User.objects.create_user(**self.user_data)
        
        # Try to create another user with same phone number
        user_data_2 = self.user_data.copy()
        user_data_2['email'] = 'different@email.com'
        user_data_2['username'] = 'different'
        user_data_2['national_id'] = '9876543210987654'
        
        with self.assertRaises(ValidationError):
            user2 = User(**user_data_2)
            user2.full_clean()
    
    def test_email_uniqueness(self):
        """Test email uniqueness constraint"""
        User.objects.create_user(**self.user_data)
        
        # Try to create another user with same email
        user_data_2 = self.user_data.copy()
        user_data_2['phone_number'] = '+250788999888'
        user_data_2['username'] = 'different'
        user_data_2['national_id'] = '9876543210987654'
        
        with self.assertRaises(ValidationError):
            user2 = User(**user_data_2)
            user2.full_clean()


class DriverProfileModelTests(TestCase):
    """
    Test cases for DriverProfile model
    """
    
    def setUp(self):
        """Set up test data"""
        self.driver_data = TEST_DRIVER_DATA.copy()
        self.driver_user = User.objects.create_user(**self.driver_data)
    
    def test_create_driver_profile_success(self):
        """Test creating driver profile"""
        profile_data = {
            'user': self.driver_user,
            'license_number': 'RW123456789',
            'license_expiry': '2025-12-31',
            'vehicle_make': 'Honda',
            'vehicle_model': 'CB 125',
            'vehicle_year': 2023,
            'vehicle_plate_number': 'RAB123C',
            'status': 'active'
        }
        
        profile = DriverProfile.objects.create(**profile_data)
        
        self.assertEqual(profile.user, self.driver_user)
        self.assertEqual(profile.license_number, 'RW123456789')
        self.assertEqual(profile.vehicle_make, 'Honda')
        self.assertEqual(profile.status, 'active')
        self.assertFalse(profile.is_online)
    
    def test_driver_profile_string_representation(self):
        """Test driver profile __str__ method"""
        profile = DriverProfile.objects.create(
            user=self.driver_user,
            license_number='RW123456789'
        )
        
        expected_str = f"Driver: {self.driver_user.get_full_name()} - RW123456789"
        self.assertEqual(str(profile), expected_str)


class AuthenticationAPITests(APITestCase):
    """
    Test cases for authentication API endpoints
    """
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.user_data = TEST_USER_DATA.copy()
        self.driver_data = TEST_DRIVER_DATA.copy()
        
        # Create test users
        self.customer_user = User.objects.create_user(**self.user_data)
        self.driver_user = User.objects.create_user(**self.driver_data)
        
        # URLs
        self.register_url = reverse('authentication:register')
        self.login_url = reverse('authentication:login')
        self.refresh_url = reverse('authentication:token_refresh')
        self.profile_url = reverse('authentication:profile')
    
    def test_user_registration_success(self):
        """Test successful user registration"""
        registration_data = {
            'email': 'newuser@safeboda.test',
            'username': 'newuser',
            'password': 'NewPassword123!',
            'password_confirm': 'NewPassword123!',
            'phone_number': '+250788111222',
            'first_name': 'New',
            'last_name': 'User',
            'national_id': '1111222233334444',
            'role': 'customer'
        }
        
        response = self.client.post(self.register_url, registration_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        
        # Verify user was created
        user = User.objects.get(email=registration_data['email'])
        self.assertEqual(user.username, registration_data['username'])
        self.assertEqual(user.role, 'customer')
    
    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch"""
        registration_data = {
            'email': 'newuser@safeboda.test',
            'username': 'newuser',
            'password': 'Password123!',
            'password_confirm': 'DifferentPassword123!',
            'phone_number': '+250788111222',
            'national_id': '1111222233334444',
        }
        
        response = self.client.post(self.register_url, registration_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)
    
    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        registration_data = {
            'email': self.user_data['email'],  # Already exists
            'username': 'newuser',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'phone_number': '+250788111222',
            'national_id': '1111222233334444',
        }
        
        response = self.client.post(self.register_url, registration_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login_success(self):
        """Test successful user login"""
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        
        response = self.client.post(self.login_url, login_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], self.user_data['email'])
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            'email': self.user_data['email'],
            'password': 'WrongPassword'
        }
        
        response = self.client.post(self.login_url, login_data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh_success(self):
        """Test token refresh functionality"""
        # First, login to get tokens
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        login_response = self.client.post(self.login_url, login_data)
        refresh_token = login_response.data['refresh']
        
        # Use refresh token to get new access token
        refresh_data = {'refresh': refresh_token}
        response = self.client.post(self.refresh_url, refresh_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_profile_access_authenticated(self):
        """Test accessing profile with authentication"""
        # Authenticate user
        self.client.force_authenticate(user=self.customer_user)
        
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.customer_user.email)
        self.assertEqual(response.data['role'], 'customer')
    
    def test_profile_access_unauthenticated(self):
        """Test accessing profile without authentication"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_profile_update_success(self):
        """Test updating user profile"""
        self.client.force_authenticate(user=self.customer_user)
        
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        
        response = self.client.patch(self.profile_url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['last_name'], 'Name')
        
        # Verify database was updated
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.first_name, 'Updated')
        self.assertEqual(self.customer_user.last_name, 'Name')


class VerificationCodeTests(TestCase):
    """
    Test cases for verification code functionality
    """
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(**TEST_USER_DATA)
    
    def test_create_verification_code(self):
        """Test creating verification code"""
        verification_code = VerificationCode.objects.create(
            user=self.user,
            verification_type='email',
            code='123456'
        )
        
        self.assertEqual(verification_code.user, self.user)
        self.assertEqual(verification_code.verification_type, 'email')
        self.assertEqual(verification_code.code, '123456')
        self.assertFalse(verification_code.is_used)
    
    def test_verification_code_string_representation(self):
        """Test verification code __str__ method"""
        verification_code = VerificationCode.objects.create(
            user=self.user,
            verification_type='phone',
            code='654321'
        )
        
        expected_str = f"Verification code for {self.user.email} (phone)"
        self.assertEqual(str(verification_code), expected_str)


class AuthenticationSerializerTests(TestCase):
    """
    Test cases for authentication serializers
    """
    
    def setUp(self):
        """Set up test data"""
        self.user_data = TEST_USER_DATA.copy()
    
    def test_user_registration_serializer_valid(self):
        """Test user registration serializer with valid data"""
        data = {
            'email': 'test@safeboda.test',
            'username': 'testuser',
            'password': 'TestPassword123!',
            'password_confirm': 'TestPassword123!',
            'phone_number': '+250788123456',
            'first_name': 'Test',
            'last_name': 'User',
            'national_id': '1234567890123456',
            'role': 'customer'
        }
        
        serializer = UserRegistrationSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, data['email'])
        self.assertEqual(user.role, 'customer')
    
    def test_user_registration_serializer_invalid_national_id(self):
        """Test registration serializer with invalid national ID"""
        data = self.user_data.copy()
        data['national_id'] = '12345'  # Too short
        data['password_confirm'] = data['password']
        
        serializer = UserRegistrationSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('national_id', serializer.errors)
    
    def test_login_serializer(self):
        """Test login serializer"""
        user = User.objects.create_user(**self.user_data)
        
        serializer = UserLoginSerializer()
        token = serializer.get_token(user)
        
        # Verify token creation
        self.assertIsNotNone(token)
        self.assertIn('token_type', token)


class AuthenticationIntegrationTests(TransactionTestCase):
    """
    Integration tests for authentication system
    """
    
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
    
    def test_full_registration_login_flow(self):
        """Test complete registration and login flow"""
        # Step 1: Register new user
        registration_data = {
            'email': 'integration@safeboda.test',
            'username': 'integration',
            'password': 'IntegrationTest123!',
            'password_confirm': 'IntegrationTest123!',
            'phone_number': '+250788999888',
            'first_name': 'Integration',
            'last_name': 'Test',
            'national_id': '9999888877776666',
            'role': 'customer'
        }
        
        register_response = self.client.post(
            reverse('authentication:register'),
            registration_data
        )
        
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        
        # Step 2: Login with registered credentials
        login_data = {
            'email': registration_data['email'],
            'password': registration_data['password']
        }
        
        login_response = self.client.post(
            reverse('authentication:login'),
            login_data
        )
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Access protected resource
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        profile_response = self.client.get(reverse('authentication:profile'))
        
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['email'], registration_data['email'])
    
    @patch('authentication.services.send_verification_email')
    def test_email_verification_flow(self, mock_send_email):
        """Test email verification process"""
        mock_send_email.return_value = True
        
        # Register user
        registration_data = {
            'email': 'verify@safeboda.test',
            'username': 'verify',
            'password': 'VerifyTest123!',
            'password_confirm': 'VerifyTest123!',
            'phone_number': '+250788777666',
            'first_name': 'Verify',
            'last_name': 'Test',
            'national_id': '7777666655554444',
            'role': 'customer'
        }
        
        response = self.client.post(
            reverse('authentication:register'),
            registration_data
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify that email sending was attempted
        mock_send_email.assert_called_once()
        
        # Get the created user
        user = User.objects.get(email=registration_data['email'])
        
        # Verify user exists and email is not verified initially
        self.assertFalse(user.email_verified)


# Performance and load testing
class AuthenticationPerformanceTests(TestCase):
    """
    Performance tests for authentication system
    """
    
    def test_bulk_user_creation_performance(self):
        """Test performance of creating multiple users"""
        import time
        
        start_time = time.time()
        
        users = []
        for i in range(100):
            user_data = {
                'email': f'user{i}@safeboda.test',
                'username': f'user{i}',
                'password': 'TestPassword123!',
                'phone_number': f'+25078812{i:04d}',
                'first_name': 'Test',
                'last_name': f'User{i}',
                'national_id': f'{i:016d}',
                'role': 'customer'
            }
            users.append(User(**user_data))
        
        User.objects.bulk_create(users)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should create 100 users in less than 1 second
        self.assertLess(execution_time, 1.0)
        
        # Verify all users were created
        self.assertEqual(User.objects.count(), 100)
    
    def test_login_performance(self):
        """Test login performance under load"""
        # Create test user
        user = User.objects.create_user(**TEST_USER_DATA)
        
        login_data = {
            'email': TEST_USER_DATA['email'],
            'password': TEST_USER_DATA['password']
        }
        
        import time
        start_time = time.time()
        
        # Simulate 50 login attempts
        for _ in range(50):
            response = self.client.post(reverse('authentication:login'), login_data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 50 logins should complete in less than 5 seconds
        self.assertLess(execution_time, 5.0)
        
        average_time = execution_time / 50
        # Each login should take less than 100ms
        self.assertLess(average_time, 0.1)