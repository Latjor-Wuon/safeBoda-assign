"""
Views for notification system
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from .models import Notification, NotificationTemplate, NotificationPreference
from .serializers import (
    NotificationSerializer, NotificationTemplateSerializer,
    NotificationPreferenceSerializer, SendNotificationSerializer,
    NotificationStatsSerializer
)
from .services import NotificationService

User = get_user_model()


@extend_schema_view(
    get=extend_schema(
        summary="Get user notifications",
        description="Retrieve notifications for the authenticated user"
    ),
    post=extend_schema(
        summary="Mark notification as read",
        description="Mark a specific notification as read"
    )
)
class UserNotificationsView(generics.ListAPIView):
    """
    View user's notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('template').order_by('-created_at')
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema(
    summary="Mark notification as read",
    description="Mark a specific notification as read by the user"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    Mark notification as read
    """
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()
        
        return Response({
            'message': 'Notification marked as read',
            'notification_id': notification_id
        }, status=status.HTTP_200_OK)
        
    except Notification.DoesNotExist:
        return Response({
            'error': 'Notification not found'
        }, status=status.HTTP_404_NOT_FOUND)


@extend_schema_view(
    get=extend_schema(
        summary="Get notification preferences",
        description="Get user's notification preferences"
    ),
    put=extend_schema(
        summary="Update notification preferences", 
        description="Update user's notification preferences"
    ),
    patch=extend_schema(
        summary="Update notification preferences", 
        description="Partially update user's notification preferences"
    )
)
class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """
    Manage user notification preferences
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        preferences, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences


@extend_schema(
    summary="Send notification",
    description="Send notification to a user (Admin only)"
)
class SendNotificationView(APIView):
    """
    Send notification via API (Admin only)
    """
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        serializer = SendNotificationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Get recipient user
                user = User.objects.get(email=serializer.validated_data['recipient_email'])
                
                # Send notification
                notification_service = NotificationService()
                results = notification_service.send_notification(
                    user=user,
                    template_name=serializer.validated_data['template_name'],
                    context=serializer.validated_data.get('context', {}),
                    channels=serializer.validated_data.get('channels')
                )
                
                return Response({
                    'message': 'Notifications sent',
                    'results': results
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        summary="List notification templates",
        description="List all notification templates (Admin only)"
    ),
    post=extend_schema(
        summary="Create notification template",
        description="Create new notification template (Admin only)"
    )
)
class NotificationTemplateListView(generics.ListCreateAPIView):
    """
    Manage notification templates (Admin only)
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema_view(
    get=extend_schema(
        summary="Get notification template",
        description="Get notification template details (Admin only)"
    ),
    put=extend_schema(
        summary="Update notification template",
        description="Update notification template (Admin only)"
    ),
    delete=extend_schema(
        summary="Delete notification template",
        description="Delete notification template (Admin only)"
    )
)
class NotificationTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage individual notification template (Admin only)
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema(
    summary="Get notification statistics",
    description="Get notification system statistics (Admin only)"
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def notification_stats(request):
    """
    Get notification statistics
    """
    # Basic stats
    total_notifications = Notification.objects.count()
    sent_notifications = Notification.objects.filter(status='sent').count()
    pending_notifications = Notification.objects.filter(status='pending').count()
    failed_notifications = Notification.objects.filter(status='failed').count()
    
    success_rate = (sent_notifications / total_notifications * 100) if total_notifications > 0 else 0
    
    # Channel stats
    sms_notifications = Notification.objects.filter(
        phone_number__isnull=False,
        phone_number__gt=''
    )
    email_notifications = Notification.objects.filter(
        email__isnull=False,
        email__gt=''
    )
    
    # Top templates
    top_templates = list(
        NotificationTemplate.objects.annotate(
            usage_count=Count('notification')
        ).values('name', 'usage_count').order_by('-usage_count')[:10]
    )
    
    stats_data = {
        'total_notifications': total_notifications,
        'sent_notifications': sent_notifications,
        'pending_notifications': pending_notifications,
        'failed_notifications': failed_notifications,
        'success_rate': round(success_rate, 2),
        'sms_sent': sms_notifications.filter(status='sent').count(),
        'email_sent': email_notifications.filter(status='sent').count(),
        'push_sent': 0,  # Placeholder
        'top_templates': top_templates
    }
    
    serializer = NotificationStatsSerializer(stats_data)
    return Response(serializer.data)