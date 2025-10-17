"""
Serializers for government integration system
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import RTDALicense, GovernmentReport, TaxRecord, SafetyIncident, EmergencyContact

User = get_user_model()


class RTDALicenseSerializer(serializers.ModelSerializer):
    """
    Serializer for RTDA licenses
    """
    holder_name = serializers.CharField(source='holder.get_full_name', read_only=True)
    holder_email = serializers.EmailField(source='holder.email', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = RTDALicense
        fields = [
            'id', 'license_number', 'license_type', 'holder', 'holder_name', 'holder_email',
            'issued_date', 'expiry_date', 'status', 'vehicle_plate_number', 'vehicle_make',
            'vehicle_model', 'vehicle_year', 'last_inspection_date', 'next_inspection_due',
            'compliance_score', 'license_document_url', 'insurance_document_url',
            'issued_by', 'notes', 'is_expired', 'days_until_expiry', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LicenseVerificationSerializer(serializers.Serializer):
    """
    Serializer for license verification requests
    """
    license_number = serializers.CharField(max_length=50)
    national_id = serializers.CharField(max_length=16)
    
    def validate_national_id(self, value):
        """Validate Rwanda National ID format"""
        if not value.isdigit() or len(value) != 16:
            raise serializers.ValidationError("National ID must be 16 digits")
        return value


class VehicleVerificationSerializer(serializers.Serializer):
    """
    Serializer for vehicle registration verification
    """
    plate_number = serializers.CharField(max_length=20)


class ComplianceCheckSerializer(serializers.Serializer):
    """
    Serializer for compliance check results
    """
    user_id = serializers.IntegerField()
    compliance_score = serializers.IntegerField()
    active_licenses = serializers.IntegerField()
    expired_licenses = serializers.IntegerField()
    recent_incidents = serializers.IntegerField()
    issues = serializers.ListField(child=serializers.CharField())
    is_compliant = serializers.BooleanField()
    last_checked = serializers.DateTimeField()


class GovernmentReportSerializer(serializers.ModelSerializer):
    """
    Serializer for government reports
    """
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    
    class Meta:
        model = GovernmentReport
        fields = [
            'id', 'report_type', 'title', 'period_start', 'period_end',
            'report_data', 'summary', 'status', 'submitted_at', 'submitted_by',
            'submitted_by_name', 'government_reference', 'government_feedback',
            'report_file_url', 'supporting_documents', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for tax records
    """
    taxpayer_name = serializers.CharField(source='taxpayer.get_full_name', read_only=True)
    taxpayer_email = serializers.EmailField(source='taxpayer.email', read_only=True)
    
    class Meta:
        model = TaxRecord
        fields = [
            'id', 'tax_type', 'tax_period_start', 'tax_period_end',
            'taxpayer', 'taxpayer_name', 'taxpayer_email', 'taxable_amount',
            'tax_rate_percent', 'tax_amount', 'ride', 'status',
            'collected_at', 'paid_to_government_at', 'government_receipt_number',
            'government_transaction_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxCalculationSerializer(serializers.Serializer):
    """
    Serializer for tax calculation requests
    """
    driver_user_id = serializers.IntegerField()
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()
    
    def validate(self, data):
        """Validate date range"""
        if data['period_start'] >= data['period_end']:
            raise serializers.ValidationError("Period start must be before period end")
        return data


class SafetyIncidentSerializer(serializers.ModelSerializer):
    """
    Serializer for safety incidents
    """
    driver_name = serializers.CharField(source='driver.get_full_name', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    
    class Meta:
        model = SafetyIncident
        fields = [
            'id', 'incident_type', 'severity', 'status', 'driver', 'driver_name',
            'customer', 'customer_name', 'ride', 'description', 'location_latitude',
            'location_longitude', 'location_address', 'incident_datetime',
            'reported_datetime', 'resolved_datetime', 'emergency_services_contacted',
            'emergency_service_type', 'police_report_number', 'resolution_notes',
            'actions_taken', 'reported_to_government', 'government_case_number',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reported_datetime', 'created_at', 'updated_at']


class EmergencyContactSerializer(serializers.ModelSerializer):
    """
    Serializer for emergency contacts
    """
    
    class Meta:
        model = EmergencyContact
        fields = [
            'id', 'contact_type', 'name', 'phone_number', 'emergency_number',
            'email', 'province', 'district', 'operating_hours',
            'response_time_minutes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmergencyReportSerializer(serializers.Serializer):
    """
    Serializer for emergency incident reporting
    """
    incident_id = serializers.UUIDField()
    location_latitude = serializers.FloatField()
    location_longitude = serializers.FloatField()
    incident_description = serializers.CharField(max_length=1000)
    
    def validate_location_latitude(self, value):
        """Validate latitude is within Rwanda"""
        if not (-3.0 <= value <= -1.0):
            raise serializers.ValidationError("Latitude must be within Rwanda boundaries")
        return value
    
    def validate_location_longitude(self, value):
        """Validate longitude is within Rwanda"""
        if not (28.8 <= value <= 30.9):
            raise serializers.ValidationError("Longitude must be within Rwanda boundaries")
        return value


class MonthlyReportRequestSerializer(serializers.Serializer):
    """
    Serializer for monthly report generation requests
    """
    year = serializers.IntegerField(min_value=2020, max_value=2030)
    month = serializers.IntegerField(min_value=1, max_value=12)
    report_type = serializers.ChoiceField(choices=[
        ('monthly_rides', 'Monthly Rides'),
        ('tax_collection', 'Tax Collection'),
        ('driver_compliance', 'Driver Compliance'),
        ('safety_incidents', 'Safety Incidents'),
    ])


class ReportSubmissionSerializer(serializers.Serializer):
    """
    Serializer for submitting reports to government
    """
    report_id = serializers.UUIDField()
    government_department = serializers.CharField(max_length=100)
    submission_notes = serializers.CharField(max_length=500, required=False, allow_blank=True)