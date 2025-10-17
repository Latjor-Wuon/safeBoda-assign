"""
Authentication models for SafeBoda Rwanda
Includes custom User model with Rwanda-specific fields and roles
"""
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.core.validators import RegexValidator
# from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
import uuid


class CustomUserManager(UserManager):
    """Custom manager for User model"""
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create and save a SuperUser with 'admin' role."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')  # Set role to admin for superusers
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with Rwanda-specific fields and role management
    """
    USER_ROLES = (
        ('customer', 'Customer'),
        ('driver', 'Driver'),
        ('admin', 'Admin'),
        ('government', 'Government Official'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(_('phone number'), max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=USER_ROLES, default='customer')
    
    # Rwanda-specific fields
    national_id = models.CharField(
        max_length=16, 
        unique=True, 
        validators=[RegexValidator(
            regex=r'^\d{16}$',
            message='Rwanda National ID must be 16 digits'
        )],
        help_text='Rwanda National ID (16 digits)'
    )
    
    # Personal information
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    middle_name = models.CharField(_('middle name'), max_length=150, blank=True)
    date_of_birth = models.DateField(_('date of birth'), null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    
    # Address information
    province = models.CharField(_('province'), max_length=100, blank=True)
    district = models.CharField(_('district'), max_length=100, blank=True)
    sector = models.CharField(_('sector'), max_length=100, blank=True)
    cell = models.CharField(_('cell'), max_length=100, blank=True)
    village = models.CharField(_('village'), max_length=100, blank=True)
    
    # Profile information
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    language_preference = models.CharField(
        max_length=10, 
        choices=[('en', 'English'), ('rw', 'Kinyarwanda'), ('fr', 'French')],
        default='rw'
    )
    
    # Account status
    is_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone_number', 'first_name', 'last_name', 'national_id']
    
    objects = CustomUserManager()  # Use custom manager
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['national_id']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        """Return full name with middle name if available"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def get_rwanda_address(self):
        """Return formatted Rwanda address"""
        parts = [self.village, self.cell, self.sector, self.district, self.province]
        return ", ".join([part for part in parts if part])


class DriverProfile(models.Model):
    """
    Extended profile for drivers with Rwanda-specific requirements
    """
    VEHICLE_TYPES = (
        ('motorcycle', 'Motorcycle'),
        ('car', 'Car'),
        ('bicycle', 'Bicycle'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    
    # Driver license information
    license_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[A-Z0-9]{8,20}$',
            message='Invalid Rwanda driver license format'
        )]
    )
    license_expiry_date = models.DateField()
    license_category = models.CharField(max_length=10)  # A, B, C, etc.
    
    # Vehicle information
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    vehicle_plate_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(
            regex=r'^R[A-Z]{2}\s?\d{3}[A-Z]$',
            message='Invalid Rwanda vehicle plate number format'
        )]
    )
    vehicle_make = models.CharField(max_length=50)
    vehicle_model = models.CharField(max_length=50)
    vehicle_year = models.PositiveIntegerField()
    vehicle_color = models.CharField(max_length=30)
    
    # Insurance and documents
    insurance_number = models.CharField(max_length=50)
    insurance_expiry_date = models.DateField()
    vehicle_inspection_date = models.DateField()
    vehicle_inspection_expiry = models.DateField()
    
    # Driver status and ratings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_rides = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Location and availability
    is_online = models.BooleanField(default=False)
    current_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_drivers')
    
    class Meta:
        db_table = 'driver_profiles'
        verbose_name = 'Driver Profile'
        verbose_name_plural = 'Driver Profiles'
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['vehicle_plate_number']),
            models.Index(fields=['status']),
            models.Index(fields=['is_online']),
        ]
    
    def __str__(self):
        return f"Driver: {self.user.full_name} - {self.vehicle_plate_number}"


class UserSession(models.Model):
    """
    Track user sessions for security and analytics
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_info = models.JSONField(default=dict, blank=True)
    location_info = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_sessions'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['user', 'is_active']),
        ]


class VerificationCode(models.Model):
    """
    Store verification codes for phone and email verification
    """
    VERIFICATION_TYPES = (
        ('phone', 'Phone Verification'),
        ('email', 'Email Verification'),
        ('password_reset', 'Password Reset'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=6)
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'verification_codes'
        verbose_name = 'Verification Code'
        verbose_name_plural = 'Verification Codes'
        indexes = [
            models.Index(fields=['user', 'verification_type', 'is_used']),
            models.Index(fields=['code', 'expires_at']),
        ]