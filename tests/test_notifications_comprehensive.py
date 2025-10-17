"""
Comprehensive unit tests for SafeBoda Rwanda notification system
Achieving 90%+ code coverage for RTDA compliance
"""


from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from notifications.models import (
    Notification, NotificationPreference, NotificationTemplate, 
    SMSNotification, PushNotification
)
from notifications.services import NotificationService, SMSService, PushNotificationService
from notifications.serializers import (
    NotificationSerializer, NotificationPreferenceSerializer,
    SMSNotificationSerializer, PushNotificationSerializer
)
from testing_framework.utils import TestDataFactory, TestAssertions


class NotificationModelTests(TestCase):
    """
    Unit tests for Notification model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.driver = self.test_factory.create_test_driver()
    
    def test_create_notification_for_customer(self):
        """Test creating notification for customer"""
        notification = Notification.objects.create(
            recipient=self.customer,
            title='Ride Confirmed',
            message='Your ride has been confirmed. Driver will arrive in 5 minutes.',
            notification_type='ride_update',
            priority='high',
            channel='push'
        )
        
        self.assertEqual(notification.recipient, self.customer)
        self.assertEqual(notification.title, 'Ride Confirmed')
        self.assertEqual(notification.notification_type, 'ride_update')
        self.assertEqual(notification.priority, 'high')
        self.assertEqual(notification.channel, 'push')
        self.assertFalse(notification.is_read)
    
    def test_create_notification_for_driver(self):
        """Test creating notification for driver"""
        notification = Notification.objects.create(
            recipient=self.driver.user,
            title='New Ride Request',
            message='You have a new ride request in Kigali.',
            notification_type='ride_request',
            priority='urgent',
            channel='sms'
        )
        
        self.assertEqual(notification.recipient, self.driver.user)
        self.assertEqual(notification.notification_type, 'ride_request')
        self.assertEqual(notification.priority, 'urgent')
        self.assertEqual(notification.channel, 'sms')
    
    def test_notification_string_representation(self):
        """Test notification __str__ method"""
        notification = Notification.objects.create(
            recipient=self.customer,
            title='Payment Received',
            message='Your payment of 1500 RWF has been processed.',
            notification_type='payment'
        )
        
        expected_str = f"{notification.title} - {self.customer.email}"
        self.assertEqual(str(notification), expected_str)
    
    def test_notification_types_validation(self):
        """Test notification type validation"""
        valid_types = [
            'ride_request', 'ride_update', 'payment', 'promotion', 
            'system', 'safety', 'verification'
        ]
        
        for notification_type in valid_types:
            notification = Notification(
                recipient=self.customer,
                title='Test Notification',
                message='Test message',
                notification_type=notification_type
            )
            notification.full_clean()  # Should not raise
    
    def test_notification_priority_levels(self):
        """Test notification priority levels"""
        priorities = ['low', 'medium', 'high', 'urgent']
        
        for priority in priorities:
            notification = Notification(
                recipient=self.customer,
                title='Test Notification',
                message='Test message',
                priority=priority
            )
            notification.full_clean()  # Should not raise
    
    def test_notification_channels(self):
        """Test notification delivery channels"""
        channels = ['push', 'sms', 'email', 'in_app']
        
        for channel in channels:
            notification = Notification(
                recipient=self.customer,
                title='Test Notification',
                message='Test message',
                channel=channel
            )
            notification.full_clean()  # Should not raise
    
    def test_mark_notification_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            recipient=self.customer,
            title='Test Notification',
            message='Test message'
        )
        
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        
        # Mark as read
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
    
    def test_notification_metadata_storage(self):
        """Test storing notification metadata"""
        metadata = {
            'ride_id': 123,
            'driver_location': {'lat': -1.9441, 'lng': 30.0619},
            'eta_minutes': 5,
            'ride_type': 'standard'
        }
        
        notification = Notification.objects.create(
            recipient=self.customer,
            title='Driver En Route',
            message='Your driver is on the way',
            notification_type='ride_update',
            metadata=metadata
        )
        
        self.assertEqual(notification.metadata['ride_id'], 123)
        self.assertEqual(notification.metadata['eta_minutes'], 5)
        self.assertIn('driver_location', notification.metadata)


class NotificationPreferenceModelTests(TestCase):
    """
    Unit tests for NotificationPreference model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
    
    def test_create_notification_preferences(self):
        """Test creating user notification preferences"""
        preferences = NotificationPreference.objects.create(
            user=self.customer,
            sms_enabled=True,
            push_enabled=True,
            email_enabled=False,
            ride_updates=True,
            payment_updates=True,
            promotional_messages=False,
            safety_alerts=True
        )
        
        self.assertEqual(preferences.user, self.customer)
        self.assertTrue(preferences.sms_enabled)
        self.assertTrue(preferences.push_enabled)
        self.assertFalse(preferences.email_enabled)
        self.assertTrue(preferences.ride_updates)
        self.assertTrue(preferences.safety_alerts)
    
    def test_notification_preference_defaults(self):
        """Test default notification preference values"""
        preferences = NotificationPreference.objects.create(
            user=self.customer
        )
        
        # Default values should be set
        self.assertTrue(preferences.sms_enabled)
        self.assertTrue(preferences.push_enabled)
        self.assertTrue(preferences.ride_updates)
        self.assertTrue(preferences.payment_updates)
        self.assertTrue(preferences.safety_alerts)
    
    def test_notification_preference_string_representation(self):
        """Test notification preference __str__ method"""
        preferences = NotificationPreference.objects.create(
            user=self.customer
        )
        
        expected_str = f"Notification Preferences - {self.customer.email}"
        self.assertEqual(str(preferences), expected_str)
    
    def test_update_notification_preferences(self):
        """Test updating notification preferences"""
        preferences = NotificationPreference.objects.create(
            user=self.customer,
            promotional_messages=True
        )
        
        # Update preferences
        preferences.promotional_messages = False
        preferences.sms_enabled = False
        preferences.save()
        
        preferences.refresh_from_db()
        self.assertFalse(preferences.promotional_messages)
        self.assertFalse(preferences.sms_enabled)


class NotificationTemplateModelTests(TestCase):
    """
    Unit tests for NotificationTemplate model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
    
    def test_create_notification_template(self):
        """Test creating notification template"""
        template = NotificationTemplate.objects.create(
            name='ride_confirmed',
            title='Ride Confirmed - #{ride_id}',
            message='Your ride has been confirmed. Driver {driver_name} will arrive in {eta} minutes.',
            notification_type='ride_update',
            language='en',
            is_active=True
        )
        
        self.assertEqual(template.name, 'ride_confirmed')
        self.assertEqual(template.language, 'en')
        self.assertTrue(template.is_active)
        self.assertIn('{driver_name}', template.message)
    
    def test_kinyarwanda_notification_template(self):
        """Test creating Kinyarwanda notification template"""
        template = NotificationTemplate.objects.create(
            name='ride_confirmed',
            title='Urugendo rwemejwe - #{ride_id}',
            message='Urugendo rwawe rwemejwe. Umushoferi {driver_name} azagera mu minota {eta}.',
            notification_type='ride_update',
            language='rw',
            is_active=True
        )
        
        self.assertEqual(template.language, 'rw')
        self.assertIn('rwemejwe', template.title)
        self.assertIn('{driver_name}', template.message)
    
    def test_template_variable_substitution(self):
        """Test template variable substitution"""
        template = NotificationTemplate.objects.create(
            name='payment_success',
            title='Payment Processed',
            message='Payment of {amount} {currency} has been successfully processed for ride #{ride_id}.',
            notification_type='payment'
        )
        
        variables = {
            'amount': '1500',
            'currency': 'RWF',
            'ride_id': '123'
        }
        
        # In real implementation, this would be handled by the service
        rendered_message = template.message.format(**variables)
        expected_message = 'Payment of 1500 RWF has been successfully processed for ride #123.'
        
        self.assertEqual(rendered_message, expected_message)


class SMSNotificationModelTests(TestCase):
    """
    Unit tests for SMSNotification model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.notification = Notification.objects.create(
            recipient=self.customer,
            title='Test SMS',
            message='Test SMS message',
            channel='sms'
        )
    
    def test_create_sms_notification(self):
        """Test creating SMS notification record"""
        sms = SMSNotification.objects.create(
            notification=self.notification,
            phone_number='+250788123456',
            message='Your SafeBoda ride is confirmed. Driver will arrive in 5 minutes.',
            provider='twilio',
            status='sent'
        )
        
        self.assertEqual(sms.notification, self.notification)
        self.assertEqual(sms.phone_number, '+250788123456')
        self.assertEqual(sms.provider, 'twilio')
        self.assertEqual(sms.status, 'sent')
    
    def test_sms_rwanda_phone_number_validation(self):
        """Test SMS phone number validation for Rwanda"""
        valid_numbers = [
            '+250788123456',  # MTN
            '+250735987654',  # Airtel
            '+250728456789',  # Tigo
        ]
        
        for phone_number in valid_numbers:
            sms = SMSNotification(
                notification=self.notification,
                phone_number=phone_number,
                message='Test message'
            )
            sms.full_clean()  # Should not raise
    
    def test_sms_status_transitions(self):
        """Test SMS status transitions"""
        sms = SMSNotification.objects.create(
            notification=self.notification,
            phone_number='+250788123456',
            message='Test message',
            status='pending'
        )
        
        # Test status transitions
        statuses = ['pending', 'sent', 'delivered', 'failed']
        
        for status in statuses:
            sms.status = status
            sms.save()
            self.assertEqual(sms.status, status)
    
    def test_sms_delivery_tracking(self):
        """Test SMS delivery tracking"""
        sms = SMSNotification.objects.create(
            notification=self.notification,
            phone_number='+250788123456',
            message='Test message',
            provider_message_id='SMS123456789',
            status='sent',
            sent_at=timezone.now()
        )
        
        self.assertIsNotNone(sms.sent_at)
        self.assertEqual(sms.provider_message_id, 'SMS123456789')
        
        # Update delivery status
        sms.status = 'delivered'
        sms.delivered_at = timezone.now()
        sms.save()
        
        self.assertEqual(sms.status, 'delivered')
        self.assertIsNotNone(sms.delivered_at)


class PushNotificationModelTests(TestCase):
    """
    Unit tests for PushNotification model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.notification = Notification.objects.create(
            recipient=self.customer,
            title='Push Notification',
            message='Test push notification',
            channel='push'
        )
    
    def test_create_push_notification(self):
        """Test creating push notification record"""
        push = PushNotification.objects.create(
            notification=self.notification,
            device_token='device_token_123456',
            platform='android',
            title='Ride Update',
            body='Your driver has arrived',
            status='sent'
        )
        
        self.assertEqual(push.notification, self.notification)
        self.assertEqual(push.device_token, 'device_token_123456')
        self.assertEqual(push.platform, 'android')
        self.assertEqual(push.status, 'sent')
    
    def test_push_notification_platforms(self):
        """Test push notification platform validation"""
        platforms = ['android', 'ios', 'web']
        
        for platform in platforms:
            push = PushNotification(
                notification=self.notification,
                device_token='token_123',
                platform=platform,
                title='Test',
                body='Test message'
            )
            push.full_clean()  # Should not raise
    
    def test_push_notification_payload(self):
        """Test push notification with custom payload"""
        custom_data = {
            'ride_id': 123,
            'action': 'view_ride',
            'sound': 'notification.wav'
        }
        
        push = PushNotification.objects.create(
            notification=self.notification,
            device_token='token_123',
            platform='ios',
            title='New Ride Request',
            body='You have a new ride request',
            payload=custom_data
        )
        
        self.assertEqual(push.payload['ride_id'], 123)
        self.assertEqual(push.payload['action'], 'view_ride')


class NotificationServiceTests(TestCase):
    """
    Unit tests for NotificationService
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.driver = self.test_factory.create_test_driver()
        self.notification_service = NotificationService()
    
    def test_send_ride_confirmation_notification(self):
        """Test sending ride confirmation notification"""
        ride = self.test_factory.create_test_ride(
            customer=self.customer,
            driver=self.driver
        )
        
        with patch.object(self.notification_service, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            result = self.notification_service.send_ride_confirmation(ride)
            
            self.assertTrue(result)
            mock_send.assert_called_once()
    
    def test_send_driver_arrival_notification(self):
        """Test sending driver arrival notification"""
        ride = self.test_factory.create_test_ride(
            customer=self.customer,
            driver=self.driver
        )
        
        with patch.object(self.notification_service, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            result = self.notification_service.send_driver_arrival(ride, eta_minutes=3)
            
            self.assertTrue(result)
            mock_send.assert_called_once()
    
    def test_send_payment_success_notification(self):
        """Test sending payment success notification"""
        from payments.models import Payment
        
        payment = Payment.objects.create(
            ride=self.test_factory.create_test_ride(customer=self.customer),
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF',
            status='completed'
        )
        
        with patch.object(self.notification_service, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            result = self.notification_service.send_payment_success(payment)
            
            self.assertTrue(result)
            mock_send.assert_called_once()
    
    def test_send_notification_with_preferences(self):
        """Test sending notification respecting user preferences"""
        # Create user preferences
        NotificationPreference.objects.create(
            user=self.customer,
            sms_enabled=True,
            push_enabled=False,
            ride_updates=True
        )
        
        notification_data = {
            'recipient': self.customer,
            'title': 'Ride Update',
            'message': 'Your ride has been confirmed',
            'notification_type': 'ride_update'
        }
        
        with patch('notifications.services.SMSService.send_sms') as mock_sms:
            with patch('notifications.services.PushNotificationService.send_push') as mock_push:
                mock_sms.return_value = True
                
                result = self.notification_service.send_notification(**notification_data)
                
                # Should send SMS but not push (based on preferences)
                mock_sms.assert_called_once()
                mock_push.assert_not_called()
    
    def test_send_bulk_notifications(self):
        """Test sending bulk notifications"""
        users = [
            self.test_factory.create_test_user(f'user{i}@example.com')
            for i in range(5)
        ]
        
        notification_data = {
            'title': 'System Maintenance',
            'message': 'SafeBoda will be under maintenance tonight',
            'notification_type': 'system'
        }
        
        with patch.object(self.notification_service, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            results = self.notification_service.send_bulk_notifications(
                users, notification_data
            )
            
            self.assertEqual(len(results), 5)
            self.assertEqual(mock_send.call_count, 5)


class SMSServiceTests(TestCase):
    """
    Unit tests for SMS service
    """
    
    def setUp(self):
        self.sms_service = SMSService()
    
    @patch('notifications.services.twilio_client.messages.create')
    def test_send_sms_success(self, mock_create):
        """Test successful SMS sending"""
        mock_message = Mock()
        mock_message.sid = 'SMS123456789'
        mock_message.status = 'queued'
        mock_create.return_value = mock_message
        
        result = self.sms_service.send_sms(
            phone_number='+250788123456',
            message='Your SafeBoda ride is confirmed'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'SMS123456789')
        mock_create.assert_called_once()
    
    @patch('notifications.services.twilio_client.messages.create')
    def test_send_sms_failure(self, mock_create):
        """Test SMS sending failure"""
        from twilio.base.exceptions import TwilioException
        mock_create.side_effect = TwilioException('Invalid phone number')
        
        result = self.sms_service.send_sms(
            phone_number='+250788123456',
            message='Test message'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_format_rwanda_phone_number(self):
        """Test Rwanda phone number formatting"""
        test_cases = [
            ('0788123456', '+250788123456'),
            ('788123456', '+250788123456'),
            ('+250788123456', '+250788123456'),
        ]
        
        for input_number, expected_output in test_cases:
            formatted = self.sms_service.format_phone_number(input_number)
            self.assertEqual(formatted, expected_output)
    
    def test_validate_rwanda_phone_number(self):
        """Test Rwanda phone number validation"""
        valid_numbers = ['+250788123456', '+250735987654', '+250728456789']
        invalid_numbers = ['+1234567890', '+250123456789', '0788123']
        
        for number in valid_numbers:
            self.assertTrue(self.sms_service.validate_phone_number(number))
        
        for number in invalid_numbers:
            self.assertFalse(self.sms_service.validate_phone_number(number))


class PushNotificationServiceTests(TestCase):
    """
    Unit tests for Push Notification service
    """
    
    def setUp(self):
        self.push_service = PushNotificationService()
    
    @patch('notifications.services.fcm_send')
    def test_send_push_notification_success(self, mock_fcm):
        """Test successful push notification sending"""
        mock_fcm.return_value = {'success': 1, 'failure': 0}
        
        result = self.push_service.send_push_notification(
            device_token='device_token_123',
            title='New Ride Request',
            body='You have a new ride request',
            platform='android'
        )
        
        self.assertTrue(result['success'])
        mock_fcm.assert_called_once()
    
    @patch('notifications.services.fcm_send')
    def test_send_push_notification_failure(self, mock_fcm):
        """Test push notification sending failure"""
        mock_fcm.return_value = {'success': 0, 'failure': 1}
        
        result = self.push_service.send_push_notification(
            device_token='invalid_token',
            title='Test',
            body='Test message',
            platform='ios'
        )
        
        self.assertFalse(result['success'])
    
    def test_build_android_payload(self):
        """Test building Android push notification payload"""
        payload = self.push_service.build_android_payload(
            title='Ride Update',
            body='Your driver has arrived',
            data={'ride_id': 123, 'action': 'view_ride'}
        )
        
        self.assertEqual(payload['notification']['title'], 'Ride Update')
        self.assertEqual(payload['data']['ride_id'], '123')  # FCM converts to string
        self.assertEqual(payload['data']['action'], 'view_ride')
    
    def test_build_ios_payload(self):
        """Test building iOS push notification payload"""
        payload = self.push_service.build_ios_payload(
            title='Payment Processed',
            body='Your payment of 1500 RWF was successful',
            data={'payment_id': 456},
            sound='notification.wav'
        )
        
        self.assertEqual(payload['aps']['alert']['title'], 'Payment Processed')
        self.assertEqual(payload['aps']['sound'], 'notification.wav')
        self.assertEqual(payload['payment_id'], 456)


class NotificationAPITests(APITestCase):
    """
    Unit tests for notification API endpoints
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        
        # Authenticate as customer
        self.client.force_authenticate(user=self.customer)
    
    def test_list_user_notifications(self):
        """Test listing user notifications"""
        # Create test notifications
        notifications = [
            Notification.objects.create(
                recipient=self.customer,
                title=f'Notification {i}',
                message=f'Test message {i}',
                notification_type='system'
            )
            for i in range(3)
        ]
        
        response = self.client.get('/api/v1/notifications/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
    
    def test_mark_notification_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            recipient=self.customer,
            title='Test Notification',
            message='Test message',
            is_read=False
        )
        
        response = self.client.patch(
            f'/api/v1/notifications/{notification.id}/',
            {'is_read': True},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_read'])
    
    def test_get_notification_preferences(self):
        """Test getting user notification preferences"""
        NotificationPreference.objects.create(
            user=self.customer,
            sms_enabled=True,
            push_enabled=False
        )
        
        response = self.client.get('/api/v1/notification-preferences/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['sms_enabled'])
        self.assertFalse(response.data['push_enabled'])
    
    def test_update_notification_preferences(self):
        """Test updating notification preferences"""
        preferences = NotificationPreference.objects.create(
            user=self.customer,
            promotional_messages=True
        )
        
        update_data = {
            'sms_enabled': False,
            'promotional_messages': False
        }
        
        response = self.client.patch(
            '/api/v1/notification-preferences/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['sms_enabled'])
        self.assertFalse(response.data['promotional_messages'])
    
    def test_send_test_notification(self):
        """Test sending test notification (admin only)"""
        admin_user = self.test_factory.create_test_user(
            email='admin@safeboda.rw',
            role='admin'
        )
        self.client.force_authenticate(user=admin_user)
        
        notification_data = {
            'recipient_id': self.customer.id,
            'title': 'Test Notification',
            'message': 'This is a test notification',
            'notification_type': 'system'
        }
        
        with patch('notifications.services.NotificationService.send_notification') as mock_send:
            mock_send.return_value = True
            
            response = self.client.post(
                '/api/v1/notifications/send-test/',
                notification_data,
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_send.assert_called_once()
    
    def test_unauthorized_access_to_notifications(self):
        """Test unauthorized access to notification endpoints"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
