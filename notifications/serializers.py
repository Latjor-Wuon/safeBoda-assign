"""
Serializers for notification system
"""

from rest_framework import serializers
from .models import Notification, NotificationTemplate, NotificationPreference, SMSProvider


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notifications
    """
    template_name = serializers.CharField(source='template.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'template_name', 'user_email', 'title', 'message',
            'status', 'priority', 'sent_at', 'delivered_at', 'read_at',
            'failure_reason', 'retry_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for notification templates
    """
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'subject', 
            'message', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for user notification preferences
    """
    
    class Meta:
        model = NotificationPreference
        fields = [
            'sms_enabled', 'email_enabled', 'push_enabled',
            'ride_updates', 'payment_updates', 'promotional_offers',
            'security_alerts', 'quiet_hours_start', 'quiet_hours_end',
            'language_preference'
        ]


class SendNotificationSerializer(serializers.Serializer):
    """
    Serializer for sending notifications via API
    """
    template_name = serializers.CharField(max_length=100)
    user_email = serializers.EmailField()
    context = serializers.JSONField(default=dict)
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=['sms', 'email', 'push', 'in_app']),
        required=False,
        allow_empty=True
    )
    
    def validate_template_name(self, value):
        """Validate that template exists and is active"""
        try:
            NotificationTemplate.objects.get(name=value, is_active=True)
        except NotificationTemplate.DoesNotExist:
            raise serializers.ValidationError(f"Template '{value}' not found or inactive")
        return value


class SMSProviderSerializer(serializers.ModelSerializer):
    """
    Serializer for SMS providers (admin only)
    """
    
    class Meta:
        model = SMSProvider
        fields = [
            'id', 'name', 'api_url', 'sender_id', 'is_active',
            'daily_limit', 'cost_per_sms', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True}
        }


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer for notification statistics
    """
    total_notifications = serializers.IntegerField()
    sent_notifications = serializers.IntegerField()
    pending_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()
    success_rate = serializers.FloatField()
    
    # By channel
    sms_sent = serializers.IntegerField()
    email_sent = serializers.IntegerField()
    push_sent = serializers.IntegerField()
    
    # By template
    top_templates = serializers.ListField(child=serializers.DictField())