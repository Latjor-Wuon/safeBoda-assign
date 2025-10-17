"""
Test notifications functionality for SafeBoda Rwanda
Comprehensive testing of notification services and models
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

from notifications.models import (
    NotificationTemplate, Notification, SMSProvider, NotificationPreference
)
from notifications.services import (
    NotificationService, SMSService, EmailService, PushNotificationService
)

User = get_user_model()


class NotificationModelsTests(TestCase):
    """Test notification models"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='user@notifications.test',
            username='user_notif',
            password='UserPass123!',
            phone_number='+250788111111',
            national_id='1111111111111111',
            first_name='Test',
            last_name='User',
            role='customer'
        )
    
    def test_notification_template_creation(self):
        """Test creating notification template"""
        template = NotificationTemplate.objects.create(
            name='ride_confirmation',
            subject='Ride Confirmed - SafeBoda',
            message='Your ride from {pickup} to {destination} has been confirmed.',
            notification_type='ride_update',
            language='en',
            is_active=True
        )
        
        self.assertEqual(template.name, 'ride_confirmation')
        self.assertEqual(template.language, 'en')
        self.assertTrue(template.is_active)
        self.assertIn('{pickup}', template.message)
    
    def test_notification_creation(self):
        """Test creating notification"""
        template = NotificationTemplate.objects.create(
            name='test_template',
            subject='Test Subject',
            message='Test message for {user_name}',
            notification_type='general',
            language='en'
        )
        
        notification = Notification.objects.create(
            user=self.user,
            template=template,
            title='Test Notification',
            message='Test message for John Doe',
            notification_type='general',
            channel='sms',
            context={'user_name': 'John Doe'},
            priority='normal'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.template, template)
        self.assertEqual(notification.channel, 'sms')
        self.assertEqual(notification.status, 'pending')
    
    def test_sms_provider_creation(self):
        """Test creating SMS provider"""
        provider = SMSProvider.objects.create(
            name='MTN Rwanda',
            provider_type='mtn',
            api_endpoint='https://api.mtn.rw/sms/v1/send',
            api_key='test_api_key',
            username='test_user',
            is_active=True,
            priority=1,
            rate_limit=100,
            cost_per_sms=25.0
        )
        
        self.assertEqual(provider.name, 'MTN Rwanda')
        self.assertEqual(provider.provider_type, 'mtn')
        self.assertTrue(provider.is_active)
        self.assertEqual(provider.priority, 1)
    
    def test_notification_preference_creation(self):
        """Test creating notification preferences"""
        preference = NotificationPreference.objects.create(
            user=self.user,
            sms_enabled=True,
            email_enabled=True,
            push_enabled=False,
            marketing_sms=False,
            marketing_email=True,
            ride_updates=True,
            payment_updates=True,
            promotional_offers=False,
            language_preference='rw'
        )
        
        self.assertEqual(preference.user, self.user)
        self.assertTrue(preference.sms_enabled)
        self.assertFalse(preference.push_enabled)
        self.assertEqual(preference.language_preference, 'rw')


class NotificationServiceTests(TestCase):
    """Test notification services"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='service@notifications.test',
            username='service_notif',
            password='ServicePass123!',
            phone_number='+250788222222',
            national_id='2222222222222222',
            first_name='Service',
            last_name='Test',
            role='customer'
        )
        
        # Create notification template
        self.template = NotificationTemplate.objects.create(
            name='ride_confirmed',
            subject='Ride Confirmed',
            message='Your ride from {pickup} to {destination} is confirmed. Driver: {driver_name}',
            notification_type='ride_update',
            language='en'
        )
        
        # Create SMS provider
        self.sms_provider = SMSProvider.objects.create(
            name='Test Provider',
            provider_type='mtn',
            api_endpoint='https://test-api.com/sms',
            api_key='test_key',
            is_active=True,
            priority=1
        )
    
    @patch('notifications.services.requests.post')
    def test_sms_service_send(self, mock_post):
        """Test SMS service sending"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success', 'message_id': '12345'}
        mock_post.return_value = mock_response
        
        sms_service = SMSService()
        result = sms_service.send_sms(
            phone_number='+250788222222',
            message='Test SMS message',
            provider=self.sms_provider
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], '12345')
        mock_post.assert_called_once()
    
    @patch('notifications.services.requests.post')
    def test_sms_service_failure(self, mock_post):
        """Test SMS service failure handling"""
        # Mock failed API response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Invalid phone number'}
        mock_post.return_value = mock_response
        
        sms_service = SMSService()
        result = sms_service.send_sms(
            phone_number='+250788222222',
            message='Test SMS message',
            provider=self.sms_provider
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    @patch('django.core.mail.send_mail')
    def test_email_service_send(self, mock_send_mail):
        """Test email service sending"""
        mock_send_mail.return_value = True
        
        email_service = EmailService()
        result = email_service.send_email(
            to_email='test@example.com',
            subject='Test Email',
            message='Test email message'
        )
        
        self.assertTrue(result['success'])
        mock_send_mail.assert_called_once()
    
    def test_notification_service_create(self):
        """Test notification service creation"""
        context = {
            'pickup': 'Kigali City Market',
            'destination': 'Kigali Airport',
            'driver_name': 'Jean Baptiste'
        }
        
        notification = NotificationService.create_notification(
            user=self.user,
            template_name='ride_confirmed',
            context=context,
            channel='sms',
            priority='high'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.template, self.template)
        self.assertEqual(notification.priority, 'high')
        self.assertIn('Kigali City Market', notification.message)
        self.assertIn('Jean Baptiste', notification.message)
    
    def test_notification_service_process_queue(self):
        """Test notification queue processing"""
        # Create pending notifications
        notifications = []
        for i in range(3):
            notification = Notification.objects.create(
                user=self.user,
                template=self.template,
                title=f'Test Notification {i}',
                message=f'Test message {i}',
                notification_type='general',
                channel='sms',
                priority='normal',
                status='pending'
            )
            notifications.append(notification)
        
        # Process queue should return pending notifications
        pending_count = NotificationService.get_pending_notifications_count()
        self.assertEqual(pending_count, 3)
    
    def test_template_rendering(self):
        """Test template message rendering with context"""
        context = {
            'pickup': 'Nyabugogo',
            'destination': 'Airport',
            'driver_name': 'Paul Kagame'
        }
        
        rendered_message = NotificationService.render_template(
            template=self.template,
            context=context
        )
        
        expected_message = "Your ride from Nyabugogo to Airport is confirmed. Driver: Paul Kagame"
        self.assertEqual(rendered_message, expected_message)
    
    def test_multilingual_template_support(self):
        """Test multilingual template support"""
        # Create Kinyarwanda template
        rw_template = NotificationTemplate.objects.create(
            name='ride_confirmed',
            subject='Urugendo Rwemewe',
            message='Urugendo rwawe kuva {pickup} kugeza {destination} rwemewe. Umushoferi: {driver_name}',
            notification_type='ride_update',
            language='rw'
        )
        
        context = {
            'pickup': 'Nyabugogo',
            'destination': 'Kanombe',
            'driver_name': 'Jean Claude'
        }
        
        # Test getting template by language
        template = NotificationService.get_template_by_language('ride_confirmed', 'rw')
        self.assertEqual(template, rw_template)
        
        rendered_message = NotificationService.render_template(
            template=rw_template,
            context=context
        )
        
        self.assertIn('Nyabugogo', rendered_message)
        self.assertIn('Jean Claude', rendered_message)
        self.assertIn('rwemewe', rendered_message)


class NotificationAPITests(APITestCase):
    """Test notification API endpoints"""
    
    def setUp(self):
        """Set up test data and authentication"""
        self.user = User.objects.create_user(
            email='api@notifications.test',
            username='api_notif',
            password='APIPass123!',
            phone_number='+250788333333',
            national_id='3333333333333333',
            first_name='API',
            last_name='Test',
            role='customer'
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create test template
        self.template = NotificationTemplate.objects.create(
            name='test_template',
            subject='Test Subject',
            message='Test message for {user_name}',
            notification_type='general',
            language='en'
        )
    
    def test_send_notification_endpoint(self):
        """Test sending notification via API"""
        url = reverse('notifications:send_notification')
        
        data = {
            'user_id': str(self.user.id),
            'template_name': 'test_template',
            'context': {'user_name': 'API Test'},
            'channel': 'sms',
            'priority': 'normal'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])
        self.assertIn('notification_id', response_data)
        
        # Verify notification was created
        notification = Notification.objects.get(id=response_data['notification_id'])
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.channel, 'sms')
    
    def test_get_user_notifications_endpoint(self):
        """Test getting user notifications"""
        # Create test notifications
        for i in range(3):
            Notification.objects.create(
                user=self.user,
                template=self.template,
                title=f'Test Notification {i}',
                message=f'Test message {i}',
                notification_type='general',
                channel='sms',
                priority='normal'
            )
        
        url = reverse('notifications:user_notifications')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(len(data['results']), 3)
        
        # Check notification structure
        notification_data = data['results'][0]
        self.assertIn('id', notification_data)
        self.assertIn('title', notification_data)
        self.assertIn('message', notification_data)
        self.assertIn('status', notification_data)
    
    def test_mark_notification_read_endpoint(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            user=self.user,
            template=self.template,
            title='Test Notification',
            message='Test message',
            notification_type='general',
            channel='sms',
            status='delivered'
        )
        
        url = reverse('notifications:mark_read', kwargs={'pk': notification.id})
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification was marked as read
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'read')
        self.assertIsNotNone(notification.read_at)
    
    def test_notification_preferences_endpoint(self):
        """Test notification preferences management"""
        url = reverse('notifications:preferences')
        
        # Test getting preferences (should create default if not exists)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test updating preferences
        data = {
            'sms_enabled': False,
            'email_enabled': True,
            'push_enabled': True,
            'marketing_sms': False,
            'ride_updates': True,
            'language_preference': 'fr'
        }
        
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify preferences were updated
        preference = NotificationPreference.objects.get(user=self.user)
        self.assertFalse(preference.sms_enabled)
        self.assertTrue(preference.email_enabled)
        self.assertEqual(preference.language_preference, 'fr')
    
    def test_notification_statistics_endpoint(self):
        """Test notification statistics endpoint"""
        # Create test notifications with different statuses
        statuses = ['pending', 'sent', 'delivered', 'failed', 'read']
        for status_name in statuses:
            Notification.objects.create(
                user=self.user,
                template=self.template,
                title=f'Test {status_name}',
                message='Test message',
                notification_type='general',
                channel='sms',
                status=status_name
            )
        
        url = reverse('notifications:statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('total_notifications', data)
        self.assertIn('status_breakdown', data)
        self.assertIn('channel_breakdown', data)
        
        # Check status breakdown
        status_breakdown = data['status_breakdown']
        self.assertEqual(status_breakdown['pending'], 1)
        self.assertEqual(status_breakdown['delivered'], 1)


class NotificationIntegrationTests(TestCase):
    """Test notification system integration"""
    
    def setUp(self):
        """Set up integration test data"""
        self.customer = User.objects.create_user(
            email='customer@integration.test',
            username='customer_integration',
            password='CustomerPass123!',
            phone_number='+250788444444',
            national_id='4444444444444444',
            first_name='Integration',
            last_name='Customer',
            role='customer'
        )
        
        self.driver = User.objects.create_user(
            email='driver@integration.test',
            username='driver_integration',
            password='DriverPass123!',
            phone_number='+250788555555',
            national_id='5555555555555555',
            first_name='Integration',
            last_name='Driver',
            role='driver'
        )
    
    def test_ride_booking_notification_flow(self):
        """Test complete notification flow for ride booking"""
        # Create ride booking template
        ride_template = NotificationTemplate.objects.create(
            name='ride_booked',
            subject='Ride Booked - SafeBoda',
            message='Your ride from {pickup} to {destination} has been booked. Fare: {fare} RWF',
            notification_type='ride_update',
            language='en'
        )
        
        # Simulate ride booking
        context = {
            'pickup': 'Kigali City Market',
            'destination': 'Kigali Airport',
            'fare': '3500'
        }
        
        # Create notification for customer
        customer_notification = NotificationService.create_notification(
            user=self.customer,
            template_name='ride_booked',
            context=context,
            channel='sms',
            priority='high'
        )
        
        self.assertEqual(customer_notification.user, self.customer)
        self.assertIn('Kigali City Market', customer_notification.message)
        self.assertIn('3500', customer_notification.message)
        self.assertEqual(customer_notification.priority, 'high')
    
    def test_multilingual_notification_flow(self):
        """Test multilingual notification support"""
        # Create templates in multiple languages
        templates = [
            ('en', 'Welcome to SafeBoda! Your account is ready.'),
            ('fr', 'Bienvenue sur SafeBoda! Votre compte est prêt.'),
            ('rw', 'Murakaza neza kuri SafeBoda! Konti yanyu itegereye.')
        ]
        
        for lang, message in templates:
            NotificationTemplate.objects.create(
                name='welcome_message',
                subject=f'Welcome - {lang.upper()}',
                message=message,
                notification_type='account',
                language=lang
            )
        
        # Test getting appropriate template based on user preference
        NotificationPreference.objects.create(
            user=self.customer,
            language_preference='rw'
        )
        
        notification = NotificationService.create_notification(
            user=self.customer,
            template_name='welcome_message',
            context={},
            channel='sms',
            priority='normal'
        )
        
        # Should use Kinyarwanda template
        self.assertIn('Murakaza neza', notification.message)
        self.assertIn('SafeBoda', notification.message)
    
    @patch('notifications.services.SMSService.send_sms')
    def test_notification_delivery_with_provider_failover(self, mock_send_sms):
        """Test notification delivery with provider failover"""
        # Create multiple SMS providers
        primary_provider = SMSProvider.objects.create(
            name='MTN Primary',
            provider_type='mtn',
            api_endpoint='https://api.mtn.rw/sms',
            api_key='primary_key',
            is_active=True,
            priority=1
        )
        
        backup_provider = SMSProvider.objects.create(
            name='Airtel Backup',
            provider_type='airtel',
            api_endpoint='https://api.airtel.rw/sms',
            api_key='backup_key',
            is_active=True,
            priority=2
        )
        
        # Mock primary provider failure, backup success
        def mock_sms_side_effect(*args, **kwargs):
            provider = kwargs.get('provider')
            if provider.name == 'MTN Primary':
                return {'success': False, 'error': 'Service unavailable'}
            else:
                return {'success': True, 'message_id': 'backup123'}
        
        mock_send_sms.side_effect = mock_sms_side_effect
        
        # Create and process notification
        template = NotificationTemplate.objects.create(
            name='test_failover',
            subject='Test',
            message='Test message',
            notification_type='general',
            language='en'
        )
        
        notification = Notification.objects.create(
            user=self.customer,
            template=template,
            title='Test',
            message='Test message',
            notification_type='general',
            channel='sms',
            priority='normal',
            status='pending'
        )
        
        # Process notification (would normally be done by background task)
        result = NotificationService.process_notification(notification)
        
        # Should succeed using backup provider
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'backup123')


class NotificationPerformanceTests(TestCase):
    """Test notification system performance"""
    
    def setUp(self):
        """Set up performance test data"""
        self.users = []
        for i in range(10):
            user = User.objects.create_user(
                email=f'user{i}@performance.test',
                username=f'user_perf_{i}',
                password='PerfPass123!',
                phone_number=f'+25078800{i:04d}',
                national_id=f'{i:016d}',
                first_name=f'User{i}',
                last_name='Performance',
                role='customer'
            )
            self.users.append(user)
        
        self.template = NotificationTemplate.objects.create(
            name='bulk_notification',
            subject='Bulk Test',
            message='Hello {user_name}, this is a test notification.',
            notification_type='general',
            language='en'
        )
    
    def test_bulk_notification_creation_performance(self):
        """Test performance of creating multiple notifications"""
        import time
        
        start_time = time.time()
        
        notifications = []
        for user in self.users:
            context = {'user_name': user.first_name}
            notification = NotificationService.create_notification(
                user=user,
                template_name='bulk_notification',
                context=context,
                channel='sms',
                priority='normal'
            )
            notifications.append(notification)
        
        execution_time = time.time() - start_time
        
        self.assertEqual(len(notifications), 10)
        self.assertLess(execution_time, 1.0)  # Should complete in under 1 second
        
        # Verify all notifications were created correctly
        for notification in notifications:
            self.assertEqual(notification.template, self.template)
            self.assertEqual(notification.status, 'pending')
    
    def test_notification_query_performance(self):
        """Test performance of notification queries"""
        import time
        
        # Create many notifications
        for user in self.users:
            for i in range(5):  # 5 notifications per user = 50 total
                Notification.objects.create(
                    user=user,
                    template=self.template,
                    title=f'Test Notification {i}',
                    message=f'Test message {i}',
                    notification_type='general',
                    channel='sms',
                    priority='normal'
                )
        
        # Test query performance
        start_time = time.time()
        
        # Query notifications for first user
        user_notifications = Notification.objects.filter(
            user=self.users[0]
        ).select_related('template').order_by('-created_at')[:10]
        
        # Force evaluation
        list(user_notifications)
        
        query_time = time.time() - start_time
        
        self.assertLess(query_time, 0.1)  # Should complete in under 100ms