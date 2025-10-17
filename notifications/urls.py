"""
URL configuration for notifications app
"""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # User notification endpoints
    path('', views.UserNotificationsView.as_view(), name='user-notifications'),
    path('<uuid:notification_id>/read/', views.mark_notification_read, name='mark-read'),
    path('preferences/', views.NotificationPreferencesView.as_view(), name='preferences'),
    
    # Admin endpoints
    path('send/', views.SendNotificationView.as_view(), name='send-notification'),
    path('templates/', views.NotificationTemplateListView.as_view(), name='template-list'),
    path('templates/<int:pk>/', views.NotificationTemplateDetailView.as_view(), name='template-detail'),
    path('stats/', views.notification_stats, name='stats'),
]