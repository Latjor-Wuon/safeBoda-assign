"""
Models for SafeBoda Rwanda notification system
Handles SMS, email, and push notifications
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class NotificationTemplate(models.Model):
    """
    Template for different types of notifications
    """
    NOTIFICATION_TYPES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
        ('ride_update', 'Ride Update'),
        ('general', 'General'),
        ('account', 'Account'),
    ]
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fr', 'French'),
        ('rw', 'Kinyarwanda'),
    ]
    
    name = models.CharField(max_length=100)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['notification_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_notification_type_display()})"


class Notification(models.Model):
    """
    Individual notification sent to users
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    
    # Content
    title = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, default='general')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='sms')
    
    # Delivery details
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    device_token = models.TextField(blank=True)
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    context = models.JSONField(default=dict, blank=True)
    external_id = models.CharField(max_length=100, blank=True)  # Provider message ID
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['template', 'created_at']),
            models.Index(fields=['priority', 'created_at']),
        ]
    
    def __str__(self):
        return f"Notification to {self.user.email} - {self.template.name}"
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at', 'updated_at'])
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at', 'updated_at'])
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at', 'updated_at'])
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at', 'updated_at'])
    
    def mark_as_failed(self, reason):
        """Mark notification as failed"""
        self.status = 'failed'
        self.failure_reason = reason
        self.retry_count += 1
        self.save(update_fields=['status', 'failure_reason', 'retry_count', 'updated_at'])


class SMSProvider(models.Model):
    """
    SMS provider configuration for Rwanda telecom providers
    """
    PROVIDER_TYPE_CHOICES = [
        ('mtn', 'MTN Rwanda'),
        ('airtel', 'Airtel Rwanda'),
        ('tigo', 'Tigo Rwanda'),
    ]
    
    name = models.CharField(max_length=50)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPE_CHOICES)
    api_endpoint = models.URLField()
    api_key = models.CharField(max_length=255)
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=255, blank=True)
    sender_id = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=1)
    rate_limit = models.PositiveIntegerField(default=10000)
    cost_per_sms = models.DecimalField(max_digits=10, decimal_places=2, default=25.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['priority']
    
    def __str__(self):
        return f"{self.name} ({self.provider_type})"


class NotificationPreference(models.Model):
    """
    User preferences for notifications
    """
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fr', 'French'),
        ('rw', 'Kinyarwanda'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Channel preferences
    sms_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    
    # Marketing preferences
    marketing_sms = models.BooleanField(default=False)
    marketing_email = models.BooleanField(default=False)
    
    # Event preferences
    ride_updates = models.BooleanField(default=True)
    payment_updates = models.BooleanField(default=True)
    promotional_offers = models.BooleanField(default=False)
    security_alerts = models.BooleanField(default=True)
    
    # Language preference
    language_preference = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    
    # Quiet hours
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"