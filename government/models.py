"""
Models for SafeBoda Rwanda government integration
Handles RTDA compliance, driver verification, and regulatory reporting
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class RTDALicense(models.Model):
    """
    RTDA (Rwanda Transport Development Agency) license management
    """
    LICENSE_TYPES = [
        ('motorcycle_taxi', 'Motorcycle Taxi License'),
        ('commercial_transport', 'Commercial Transport License'),
        ('driving_school', 'Driving School License'),
        ('vehicle_inspection', 'Vehicle Inspection License'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
        ('pending', 'Pending Approval'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license_number = models.CharField(max_length=50, unique=True)
    license_type = models.CharField(max_length=30, choices=LICENSE_TYPES)
    holder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rtda_licenses')
    
    # License details
    issued_date = models.DateTimeField()
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Vehicle information (for vehicle-related licenses)
    vehicle_plate_number = models.CharField(max_length=20, blank=True)
    vehicle_make = models.CharField(max_length=50, blank=True)
    vehicle_model = models.CharField(max_length=50, blank=True)
    vehicle_year = models.PositiveIntegerField(null=True, blank=True)
    
    # Compliance tracking
    last_inspection_date = models.DateTimeField(null=True, blank=True)
    next_inspection_due = models.DateTimeField(null=True, blank=True)
    compliance_score = models.PositiveIntegerField(default=100, help_text="Score out of 100")
    
    # Documents
    license_document_url = models.URLField(blank=True)
    insurance_document_url = models.URLField(blank=True)
    
    # Metadata
    issued_by = models.CharField(max_length=100, default="RTDA Rwanda")
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['holder', 'status']),
            models.Index(fields=['status', 'expiry_date']),
            models.Index(fields=['vehicle_plate_number']),
        ]
    
    def __str__(self):
        return f"{self.license_number} - {self.holder.get_full_name()}"
    
    @property
    def is_expired(self):
        """Check if license is expired"""
        return self.expiry_date < timezone.now()
    
    @property
    def days_until_expiry(self):
        """Days until license expires"""
        if self.is_expired:
            return 0
        return (self.expiry_date - timezone.now()).days


class GovernmentReport(models.Model):
    """
    Government compliance and tax reports
    """
    REPORT_TYPES = [
        ('monthly_rides', 'Monthly Rides Report'),
        ('tax_collection', 'Tax Collection Report'),
        ('driver_compliance', 'Driver Compliance Report'),
        ('safety_incidents', 'Safety Incidents Report'),
        ('revenue_summary', 'Revenue Summary Report'),
        ('vehicle_inspection', 'Vehicle Inspection Report'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('submitted', 'Submitted to Government'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    
    # Reporting period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Report data
    report_data = models.JSONField(help_text="Structured report data")
    summary = models.TextField()
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Government tracking
    government_reference = models.CharField(max_length=100, blank=True)
    government_feedback = models.TextField(blank=True)
    
    # File attachments
    report_file_url = models.URLField(blank=True)
    supporting_documents = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['report_type', 'period_start']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.period_start.strftime('%Y-%m')})"


class EmergencyContact(models.Model):
    """
    Emergency services and contacts for safety compliance
    """
    CONTACT_TYPES = [
        ('police', 'Rwanda National Police'),
        ('medical', 'Emergency Medical Services'),
        ('fire', 'Fire and Rescue Services'),
        ('rtda', 'RTDA Emergency Line'),
        ('safeboda', 'SafeBoda Emergency Support'),
    ]
    
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPES, unique=True)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    emergency_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    
    # Location coverage
    province = models.CharField(max_length=50, blank=True)
    district = models.CharField(max_length=50, blank=True)
    
    # Additional info
    operating_hours = models.CharField(max_length=100, default="24/7")
    response_time_minutes = models.PositiveIntegerField(help_text="Average response time in minutes")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()})"


class SafetyIncident(models.Model):
    """
    Safety incidents reporting for government compliance
    """
    INCIDENT_TYPES = [
        ('accident', 'Traffic Accident'),
        ('theft', 'Theft or Robbery'),
        ('harassment', 'Driver/Customer Harassment'),
        ('vehicle_breakdown', 'Vehicle Breakdown'),
        ('medical_emergency', 'Medical Emergency'),
        ('other', 'Other Safety Incident'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low - Minor Issue'),
        ('medium', 'Medium - Requires Attention'),
        ('high', 'High - Serious Incident'),
        ('critical', 'Critical - Emergency Response'),
    ]
    
    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('escalated', 'Escalated to Authorities'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic incident info
    incident_type = models.CharField(max_length=20, choices=INCIDENT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='reported')
    
    # Parties involved
    driver = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='driver_incidents'
    )
    customer = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='customer_incidents'
    )
    
    # Related ride (if applicable)
    ride = models.ForeignKey(
        'bookings.Ride', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='safety_incidents'
    )
    
    # Incident details
    description = models.TextField()
    location_latitude = models.FloatField(null=True, blank=True)
    location_longitude = models.FloatField(null=True, blank=True)
    location_address = models.CharField(max_length=300, blank=True)
    
    # Timeline
    incident_datetime = models.DateTimeField()
    reported_datetime = models.DateTimeField(auto_now_add=True)
    resolved_datetime = models.DateTimeField(null=True, blank=True)
    
    # Response tracking
    emergency_services_contacted = models.BooleanField(default=False)
    emergency_service_type = models.CharField(max_length=20, blank=True)
    police_report_number = models.CharField(max_length=50, blank=True)
    
    # Resolution
    resolution_notes = models.TextField(blank=True)
    actions_taken = models.JSONField(default=list, blank=True)
    
    # Government reporting
    reported_to_government = models.BooleanField(default=False)
    government_case_number = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['incident_type', 'severity']),
            models.Index(fields=['status', 'incident_datetime']),
            models.Index(fields=['driver', 'incident_datetime']),
            models.Index(fields=['reported_to_government']),
        ]
    
    def __str__(self):
        return f"{self.get_incident_type_display()} - {self.incident_datetime.strftime('%Y-%m-%d %H:%M')}"


class TaxRecord(models.Model):
    """
    Tax collection and reporting for government compliance
    """
    TAX_TYPES = [
        ('ride_tax', 'Per-Ride Tax'),
        ('driver_license_fee', 'Driver License Fee'),
        ('vehicle_registration', 'Vehicle Registration Tax'),
        ('income_tax', 'Driver Income Tax'),
        ('platform_tax', 'Platform Operation Tax'),
    ]
    
    STATUS_CHOICES = [
        ('calculated', 'Calculated'),
        ('collected', 'Collected'),
        ('paid_to_government', 'Paid to Government'),
        ('disputed', 'Disputed'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tax details
    tax_type = models.CharField(max_length=25, choices=TAX_TYPES)
    tax_period_start = models.DateTimeField()
    tax_period_end = models.DateTimeField()
    
    # Taxpayer (can be driver or platform)
    taxpayer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tax_records')
    
    # Financial details
    taxable_amount = models.DecimalField(max_digits=15, decimal_places=2)
    tax_rate_percent = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Related records
    ride = models.ForeignKey(
        'bookings.Ride', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tax_records'
    )
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='calculated')
    collected_at = models.DateTimeField(null=True, blank=True)
    paid_to_government_at = models.DateTimeField(null=True, blank=True)
    
    # Government references
    government_receipt_number = models.CharField(max_length=100, blank=True)
    government_transaction_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['tax_type', 'tax_period_start']),
            models.Index(fields=['taxpayer', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_tax_type_display()} - {self.taxpayer.get_full_name()} - {self.tax_amount} RWF"