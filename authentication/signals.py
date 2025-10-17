"""
Authentication signals for SafeBoda Rwanda
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import DriverProfile
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Handle user post-save actions
    """
    if created:
        logger.info(f"New user created: {instance.email} (Role: {instance.role})")
        
        # Additional setup for different user types can be added here
        # For example, creating driver profiles, sending welcome emails, etc.


@receiver(post_save, sender=DriverProfile)
def driver_profile_post_save(sender, instance, created, **kwargs):
    """
    Handle driver profile post-save actions
    """
    if created:
        logger.info(f"Driver profile created: {instance.user.email}")
        
        # Send notification to admin for approval
        # This could trigger a Celery task for async processing
    
    elif instance.status == 'approved' and 'approved_at' in kwargs.get('update_fields', []):
        logger.info(f"Driver approved: {instance.user.email}")
        
        # Send approval notification to driver
        # This could trigger SMS/Email notification