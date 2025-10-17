"""
Views for government integration system
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from .models import RTDALicense, GovernmentReport, TaxRecord, SafetyIncident, EmergencyContact
from .serializers import (
    RTDALicenseSerializer, LicenseVerificationSerializer, VehicleVerificationSerializer,
    ComplianceCheckSerializer, GovernmentReportSerializer, TaxRecordSerializer,
    TaxCalculationSerializer, SafetyIncidentSerializer, EmergencyContactSerializer,
    EmergencyReportSerializer, MonthlyReportRequestSerializer, ReportSubmissionSerializer
)
from .services import (
    RTDAComplianceService, TaxCalculationService, GovernmentReportingService,
    EmergencyServicesIntegration
)


# RTDA Compliance Views
@extend_schema(
    summary="Verify driver license with RTDA",
    description="Verify driver license against RTDA database for compliance"
)
class LicenseVerificationView(APIView):
    """
    Verify driver license with RTDA
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = LicenseVerificationSerializer(data=request.data)
        if serializer.is_valid():
            rtda_service = RTDAComplianceService()
            verification_result = rtda_service.verify_driver_license(
                license_number=serializer.validated_data['license_number'],
                national_id=serializer.validated_data['national_id']
            )
            
            return Response(verification_result, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Verify vehicle registration",
    description="Verify vehicle registration with RTDA database"
)
class VehicleVerificationView(APIView):
    """
    Verify vehicle registration with RTDA
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = VehicleVerificationSerializer(data=request.data)
        if serializer.is_valid():
            rtda_service = RTDAComplianceService()
            verification_result = rtda_service.verify_vehicle_registration(
                plate_number=serializer.validated_data['plate_number']
            )
            
            return Response(verification_result, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Check driver compliance status",
    description="Check overall compliance status for a driver with RTDA requirements"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def driver_compliance_check(request, driver_id):
    """
    Check driver compliance status
    """
    rtda_service = RTDAComplianceService()
    compliance_result = rtda_service.check_compliance_status(driver_id)
    
    serializer = ComplianceCheckSerializer(compliance_result)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        summary="List RTDA licenses",
        description="List all RTDA licenses (Admin only)"
    ),
    post=extend_schema(
        summary="Create RTDA license",
        description="Create new RTDA license record (Admin only)"
    )
)
class RTDALicenseListView(generics.ListCreateAPIView):
    """
    Manage RTDA licenses (Admin only)
    """
    serializer_class = RTDALicenseSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = RTDALicense.objects.select_related('holder')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by license type
        license_type = self.request.query_params.get('license_type')
        if license_type:
            queryset = queryset.filter(license_type=license_type)
        
        return queryset.order_by('-created_at')


@extend_schema_view(
    get=extend_schema(
        summary="Get RTDA license details",
        description="Get RTDA license details (Admin only)"
    ),
    put=extend_schema(
        summary="Update RTDA license",
        description="Update RTDA license (Admin only)"
    ),
    delete=extend_schema(
        summary="Delete RTDA license",
        description="Delete RTDA license (Admin only)"
    )
)
class RTDALicenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage individual RTDA license (Admin only)
    """
    queryset = RTDALicense.objects.select_related('holder')
    serializer_class = RTDALicenseSerializer
    permission_classes = [permissions.IsAdminUser]


# Tax Management Views
@extend_schema(
    summary="Calculate driver income tax",
    description="Calculate income tax for a driver over a specific period (Admin only)"
)
class TaxCalculationView(APIView):
    """
    Calculate taxes for drivers
    """
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        serializer = TaxCalculationSerializer(data=request.data)
        if serializer.is_valid():
            tax_service = TaxCalculationService()
            calculation_result = tax_service.calculate_driver_income_tax(
                driver_user_id=serializer.validated_data['driver_user_id'],
                period_start=serializer.validated_data['period_start'],
                period_end=serializer.validated_data['period_end']
            )
            
            # Create tax record if calculation successful
            if 'error' not in calculation_result:
                tax_record = tax_service.create_tax_records(calculation_result)
                if tax_record:
                    calculation_result['tax_record_id'] = str(tax_record.id)
            
            return Response(calculation_result, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        summary="List tax records",
        description="List all tax records (Admin only)"
    )
)
class TaxRecordListView(generics.ListAPIView):
    """
    List tax records (Admin only)
    """
    serializer_class = TaxRecordSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = TaxRecord.objects.select_related('taxpayer', 'ride')
        
        # Filter by tax type
        tax_type = self.request.query_params.get('tax_type')
        if tax_type:
            queryset = queryset.filter(tax_type=tax_type)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by taxpayer
        taxpayer_id = self.request.query_params.get('taxpayer_id')
        if taxpayer_id:
            queryset = queryset.filter(taxpayer_id=taxpayer_id)
        
        return queryset.order_by('-created_at')


# Government Reporting Views
@extend_schema(
    summary="Generate monthly government report",
    description="Generate monthly report for government submission (Admin only)"
)
class GenerateReportView(APIView):
    """
    Generate government reports
    """
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        serializer = MonthlyReportRequestSerializer(data=request.data)
        if serializer.is_valid():
            reporting_service = GovernmentReportingService()
            
            year = serializer.validated_data['year']
            month = serializer.validated_data['month']
            report_type = serializer.validated_data['report_type']
            
            try:
                if report_type == 'monthly_rides':
                    report = reporting_service.generate_monthly_rides_report(year, month)
                elif report_type == 'tax_collection':
                    report = reporting_service.generate_tax_collection_report(year, month)
                else:
                    return Response({
                        'error': f'Report type {report_type} not implemented yet'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                serializer = GovernmentReportSerializer(report)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Submit report to government",
    description="Submit generated report to government authorities (Admin only)"
)
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def submit_report_to_government(request):
    """
    Submit report to government
    """
    serializer = ReportSubmissionSerializer(data=request.data)
    if serializer.is_valid():
        try:
            report = GovernmentReport.objects.get(
                id=serializer.validated_data['report_id']
            )
            
            # Update report status
            report.status = 'submitted'
            report.submitted_at = timezone.now()
            report.submitted_by = request.user
            report.save()
            
            # In production, would make actual API call to government system
            
            return Response({
                'message': 'Report submitted to government successfully',
                'report_id': str(report.id),
                'submitted_at': report.submitted_at.isoformat()
            }, status=status.HTTP_200_OK)
            
        except GovernmentReport.DoesNotExist:
            return Response({
                'error': 'Report not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        summary="List government reports",
        description="List all government reports (Admin only)"
    )
)
class GovernmentReportListView(generics.ListAPIView):
    """
    List government reports (Admin only)
    """
    serializer_class = GovernmentReportSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = GovernmentReport.objects.select_related('submitted_by')
        
        # Filter by report type
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


# Safety and Emergency Views
@extend_schema_view(
    get=extend_schema(
        summary="List safety incidents",
        description="List safety incidents for compliance reporting"
    ),
    post=extend_schema(
        summary="Create safety incident report",
        description="Create new safety incident report"
    )
)
class SafetyIncidentListView(generics.ListCreateAPIView):
    """
    Manage safety incidents
    """
    serializer_class = SafetyIncidentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Regular users can only see their own incidents
        if user.role in ['customer', 'driver']:
            return SafetyIncident.objects.filter(
                Q(driver=user) | Q(customer=user)
            ).select_related('driver', 'customer', 'ride').order_by('-incident_datetime')
        
        # Admin can see all incidents
        queryset = SafetyIncident.objects.select_related('driver', 'customer', 'ride')
        
        # Filter by incident type
        incident_type = self.request.query_params.get('incident_type')
        if incident_type:
            queryset = queryset.filter(incident_type=incident_type)
        
        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        return queryset.order_by('-incident_datetime')


@extend_schema(
    summary="Report emergency incident",
    description="Report safety incident to emergency services"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def report_emergency_incident(request):
    """
    Report incident to emergency services
    """
    serializer = EmergencyReportSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Get the incident
            incident = SafetyIncident.objects.get(
                id=serializer.validated_data['incident_id']
            )
            
            # Report to emergency services
            emergency_service = EmergencyServicesIntegration()
            response = emergency_service.report_emergency_incident(incident)
            
            # Update incident with emergency response details
            if 'emergency_case_id' in response:
                incident.emergency_services_contacted = True
                incident.government_case_number = response['emergency_case_id']
                incident.save()
            
            return Response({
                'message': 'Incident reported to emergency services',
                'emergency_response': response
            }, status=status.HTTP_200_OK)
            
        except SafetyIncident.DoesNotExist:
            return Response({
                'error': 'Incident not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get emergency services",
    description="Get nearest emergency services for a location"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_emergency_services(request):
    """
    Get emergency services for location
    """
    latitude = request.query_params.get('latitude')
    longitude = request.query_params.get('longitude')
    
    if not latitude or not longitude:
        return Response({
            'error': 'Latitude and longitude are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        emergency_service = EmergencyServicesIntegration()
        services = emergency_service.get_nearest_emergency_services(
            float(latitude), 
            float(longitude)
        )
        
        return Response({
            'location': {'latitude': float(latitude), 'longitude': float(longitude)},
            'emergency_services': services
        }, status=status.HTTP_200_OK)
        
    except ValueError:
        return Response({
            'error': 'Invalid latitude or longitude format'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    get=extend_schema(
        summary="List emergency contacts",
        description="List all emergency service contacts"
    )
)
class EmergencyContactListView(generics.ListAPIView):
    """
    List emergency contacts
    """
    queryset = EmergencyContact.objects.filter(is_active=True)
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]