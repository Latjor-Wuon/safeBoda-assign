"""
Notification services for SafeBoda Rwanda
Handles SMS, email, and push notification delivery
"""

import requests
import json
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.utils import timezone
from .models import Notification, NotificationTemplate, SMSProvider, NotificationPreference

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Main service for sending notifications
    """
    
    def __init__(self):
        self.sms_service = SMSService()
        self.email_service = EmailService()
        self.push_service = PushNotificationService()
    
    def send_notification(self, 
                         user, 
                         template_name: str, 
                         context: Dict[str, Any],
                         channels: List[str] = None) -> Dict[str, bool]:
        """
        Send notification through specified channels
        
        Args:
            user: User object
            template_name: Name of the notification template
            context: Context data for template rendering
            channels: List of channels ['sms', 'email', 'push', 'in_app']
        
        Returns:
            Dict with channel success status
        """
        try:
            template = NotificationTemplate.objects.get(
                name=template_name,
                is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template '{template_name}' not found")
            return {}
        
        # Get user preferences
        preferences = self._get_user_preferences(user)
        
        # Default to template's notification type if no channels specified
        if not channels:
            channels = [template.notification_type]
        
        results = {}
        
        for channel in channels:
            if not self._should_send_notification(user, channel, preferences):
                results[channel] = False
                continue
            
            try:
                # Create notification record
                notification = self._create_notification(user, template, context, channel)
                
                # Send based on channel
                if channel == 'sms':
                    success = self.sms_service.send_sms(notification)
                elif channel == 'email':
                    success = self.email_service.send_email(notification)
                elif channel == 'push':
                    success = self.push_service.send_push(notification)
                elif channel == 'in_app':
                    success = True  # In-app notifications are just stored in DB
                    notification.mark_as_delivered()
                else:
                    success = False
                
                results[channel] = success
                
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                if 'notification' in locals():
                    notification.mark_as_failed(str(e))
                results[channel] = False
        
        return results
    
    def _get_user_preferences(self, user) -> NotificationPreference:
        """Get or create user notification preferences"""
        preferences, _ = NotificationPreference.objects.get_or_create(user=user)
        return preferences
    
    def _should_send_notification(self, user, channel: str, preferences: NotificationPreference) -> bool:
        """Check if notification should be sent based on user preferences"""
        if channel == 'sms' and not preferences.sms_enabled:
            return False
        if channel == 'email' and not preferences.email_enabled:
            return False
        if channel == 'push' and not preferences.push_enabled:
            return False
        
        # Check quiet hours
        if preferences.quiet_hours_start and preferences.quiet_hours_end:
            current_time = timezone.now().time()
            if preferences.quiet_hours_start <= current_time <= preferences.quiet_hours_end:
                return False
        
        return True
    
    def _create_notification(self, user, template: NotificationTemplate, context: Dict, channel: str) -> Notification:
        """Create notification record in database"""
        # Render templates
        subject = ""
        if template.subject_template:
            subject_tmpl = Template(template.subject_template)
            subject = subject_tmpl.render(Context(context))
        
        body_tmpl = Template(template.body_template)
        body = body_tmpl.render(Context(context))
        
        notification = Notification.objects.create(
            recipient=user,
            template=template,
            subject=subject,
            body=body,
            phone_number=user.phone_number if channel == 'sms' else '',
            email=user.email if channel == 'email' else '',
            context_data=context
        )
        
        return notification


class SMSService:
    """
    SMS service for Rwanda telecom providers
    """
    
    def send_sms(self, notification: Notification) -> bool:
        """
        Send SMS notification
        """
        try:
            # Get active SMS provider
            provider = SMSProvider.objects.filter(is_active=True).first()
            if not provider:
                logger.error("No active SMS provider configured")
                notification.mark_as_failed("No active SMS provider")
                return False
            
            # Prepare SMS data
            sms_data = {
                'to': notification.phone_number,
                'message': notification.body,
                'sender_id': provider.sender_id
            }
            
            # Send SMS based on provider
            if provider.name == 'mtn_rwanda':
                success = self._send_mtn_sms(provider, sms_data, notification)
            elif provider.name == 'airtel_rwanda':
                success = self._send_airtel_sms(provider, sms_data, notification)
            else:
                success = self._send_generic_sms(provider, sms_data, notification)
            
            return success
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            notification.mark_as_failed(str(e))
            return False
    
    def _send_mtn_sms(self, provider: SMSProvider, data: Dict, notification: Notification) -> bool:
        """Send SMS via MTN Rwanda API"""
        try:
            headers = {
                'Authorization': f'Bearer {provider.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'msisdn': data['to'],
                'message': data['message'],
                'sender_id': data['sender_id']
            }
            
            response = requests.post(
                provider.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                notification.external_id = result.get('message_id', '')
                notification.mark_as_sent()
                return True
            else:
                notification.mark_as_failed(f"MTN API error: {response.text}")
                return False
                
        except Exception as e:
            notification.mark_as_failed(f"MTN SMS error: {e}")
            return False
    
    def _send_airtel_sms(self, provider: SMSProvider, data: Dict, notification: Notification) -> bool:
        """Send SMS via Airtel Rwanda API"""
        # Similar implementation for Airtel
        # For demo, we'll simulate success
        notification.mark_as_sent()
        return True
    
    def _send_generic_sms(self, provider: SMSProvider, data: Dict, notification: Notification) -> bool:
        """Send SMS via generic provider"""
        # Generic SMS implementation
        notification.mark_as_sent()
        return True


class EmailService:
    """
    Email notification service
    """
    
    def send_email(self, notification: Notification) -> bool:
        """
        Send email notification
        """
        try:
            send_mail(
                subject=notification.subject,
                message=notification.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.email],
                fail_silently=False,
            )
            
            notification.mark_as_sent()
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            notification.mark_as_failed(str(e))
            return False


class PushNotificationService:
    """
    Push notification service for mobile apps
    """
    
    def send_push(self, notification: Notification) -> bool:
        """
        Send push notification
        """
        try:
            # This would integrate with Firebase Cloud Messaging (FCM) 
            # or Apple Push Notification Service (APNS)
            
            # For demo purposes, we'll simulate success
            notification.mark_as_sent()
            return True
            
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            notification.mark_as_failed(str(e))
            return False


# Convenience functions for common notifications
def send_ride_status_notification(ride, status_change: str):
    """Send notification when ride status changes"""
    from authentication.models import User
    
    notification_service = NotificationService()
    
    # Notify customer
    if ride.customer:
        context = {
            'user_name': ride.customer.get_full_name(),
            'ride_id': str(ride.id),
            'status': status_change,
            'driver_name': ride.driver.get_full_name() if ride.driver else 'TBD',
            'pickup_location': ride.pickup_address,
            'destination': ride.destination_address,
        }
        
        notification_service.send_notification(
            user=ride.customer,
            template_name='ride_status_update',
            context=context,
            channels=['sms', 'push', 'in_app']
        )
    
    # Notify driver
    if ride.driver and status_change in ['requested', 'cancelled']:
        context = {
            'user_name': ride.driver.get_full_name(),
            'ride_id': str(ride.id),
            'status': status_change,
            'customer_name': ride.customer.get_full_name(),
            'pickup_location': ride.pickup_address,
            'destination': ride.destination_address,
        }
        
        notification_service.send_notification(
            user=ride.driver,
            template_name='driver_ride_notification',
            context=context,
            channels=['sms', 'push', 'in_app']
        )


def send_payment_notification(transaction):
    """Send notification for payment events"""
    notification_service = NotificationService()
    
    context = {
        'user_name': transaction.user.get_full_name(),
        'amount': transaction.amount,
        'currency': 'RWF',
        'transaction_id': str(transaction.id),
        'payment_method': transaction.payment_method.get_method_display(),
        'status': transaction.get_status_display(),
    }
    
    notification_service.send_notification(
        user=transaction.user,
        template_name='payment_notification',
        context=context,
        channels=['sms', 'email', 'in_app']
    )