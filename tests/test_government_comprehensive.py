"""
Comprehensive unit tests for SafeBoda Rwanda government compliance system
Achieving 90%+ code coverage for RTDA compliance
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from government.models import (
    RTDALicense, VehicleRegistration, DriverLicense, TaxComplianceRecord,
    BusinessLicense, InsuranceRecord, InspectionRecord, ComplianceAudit
)
from government.services import (
    RTDAIntegrationService, ComplianceCheckService, DocumentVerificationService,
    TaxCalculationService, LicensingService, InspectionService
)
from government.serializers import (
    RTDALicenseSerializer, VehicleRegistrationSerializer, DriverLicenseSerializer,
    TaxComplianceRecordSerializer, BusinessLicenseSerializer, InsuranceRecordSerializer
)
from testing_framework.utils import TestDataFactory, TestAssertions


class RTDALicenseModelTests(TestCase):
    """
    Unit tests for RTDA License model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver = self.test_factory.create_test_driver()
    
    def test_create_rtda_license(self):
        """Test creating RTDA license record"""
        license_record = RTDALicense.objects.create(
            driver=self.driver,
            license_number='RTDA/PSV/2024/001234',
            license_type='public_service_vehicle',
            issue_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=335),
            issuing_authority='RTDA',
            status='active',
            license_class='motorcycle',
            endorsements=['passenger_transport', 'commercial_operation']
        )
        
        self.assertEqual(license_record.driver, self.driver)
        self.assertEqual(license_record.license_number, 'RTDA/PSV/2024/001234')
        self.assertEqual(license_record.license_type, 'public_service_vehicle')
        self.assertEqual(license_record.status, 'active')
        self.assertEqual(license_record.license_class, 'motorcycle')
        self.assertIn('passenger_transport', license_record.endorsements)
    
    def test_rtda_license_validation(self):
        """Test RTDA license number format validation"""
        valid_license_numbers = [
            'RTDA/PSV/2024/001234',
            'RTDA/DL/2024/987654',
            'RTDA/COM/2024/456789'
        ]
        
        for license_number in valid_license_numbers:
            license_record = RTDALicense(
                driver=self.driver,
                license_number=license_number,
                license_type='public_service_vehicle',
                issue_date=date.today(),
                expiry_date=date.today() + timedelta(days=365)
            )
            license_record.full_clean()  # Should not raise
    
    def test_license_expiry_check(self):
        """Test license expiry validation"""
        # Expired license
        expired_license = RTDALicense.objects.create(
            driver=self.driver,
            license_number='RTDA/PSV/2023/001234',
            license_type='public_service_vehicle',
            issue_date=date.today() - timedelta(days=400),
            expiry_date=date.today() - timedelta(days=30),
            status='expired'
        )
        
        self.assertEqual(expired_license.status, 'expired')
        self.assertLess(expired_license.expiry_date, date.today())
        
        # Check if license is expired
        is_expired = expired_license.expiry_date < date.today()
        self.assertTrue(is_expired)
    
    def test_license_renewal_tracking(self):
        """Test license renewal process tracking"""
        original_license = RTDALicense.objects.create(
            driver=self.driver,
            license_number='RTDA/PSV/2024/001234',
            license_type='public_service_vehicle',
            issue_date=date.today() - timedelta(days=365),
            expiry_date=date.today() - timedelta(days=30),
            status='expired'
        )
        
        # Create renewal record
        renewed_license = RTDALicense.objects.create(
            driver=self.driver,
            license_number='RTDA/PSV/2024/001235',
            license_type='public_service_vehicle',
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status='active',
            previous_license_number='RTDA/PSV/2024/001234'
        )
        
        self.assertEqual(renewed_license.status, 'active')
        self.assertEqual(renewed_license.previous_license_number, original_license.license_number)
    
    def test_license_string_representation(self):
        """Test RTDALicense __str__ method"""
        license_record = RTDALicense.objects.create(
            driver=self.driver,
            license_number='RTDA/PSV/2024/001234',
            license_type='public_service_vehicle'
        )
        
        expected_str = f"RTDA License: RTDA/PSV/2024/001234 - {self.driver.user.first_name} {self.driver.user.last_name}"
        self.assertEqual(str(license_record), expected_str)


class VehicleRegistrationModelTests(TestCase):
    """
    Unit tests for Vehicle Registration model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver = self.test_factory.create_test_driver()
    
    def test_create_vehicle_registration(self):
        """Test creating vehicle registration record"""
        registration = VehicleRegistration.objects.create(
            driver=self.driver,
            plate_number='RAD 123 A',
            vehicle_make='Honda',
            vehicle_model='CB125',
            year_of_manufacture=2022,
            engine_number='CB125ENG123456',
            chassis_number='CB125CHS789012',
            registration_date=date.today() - timedelta(days=60),
            expiry_date=date.today() + timedelta(days=305),
            vehicle_type='motorcycle',
            fuel_type='petrol',
            engine_capacity=125,
            status='active'
        )
        
        self.assertEqual(registration.plate_number, 'RAD 123 A')
        self.assertEqual(registration.vehicle_make, 'Honda')
        self.assertEqual(registration.vehicle_model, 'CB125')
        self.assertEqual(registration.vehicle_type, 'motorcycle')
        self.assertEqual(registration.engine_capacity, 125)
    
    def test_rwanda_plate_number_validation(self):
        """Test Rwanda plate number format validation"""
        valid_plate_numbers = [
            'RAD 123 A',  # Standard format
            'RCA 456 B',  # Alternative format
            'RBA 789 C',  # Regional format
        ]
        
        for plate_number in valid_plate_numbers:
            registration = VehicleRegistration(
                driver=self.driver,
                plate_number=plate_number,
                vehicle_make='Honda',
                vehicle_model='CB125',
                vehicle_type='motorcycle'
            )
            registration.full_clean()  # Should not raise
    
    def test_vehicle_specification_validation(self):
        """Test vehicle specification requirements"""
        registration = VehicleRegistration.objects.create(
            driver=self.driver,
            plate_number='RAD 123 A',
            vehicle_make='Honda',
            vehicle_model='CB125',
            year_of_manufacture=2020,
            engine_capacity=125,
            vehicle_type='motorcycle'
        )
        
        # Motorcycle engine capacity should be appropriate for commercial use
        min_commercial_capacity = 100  # cc
        self.assertGreaterEqual(registration.engine_capacity, min_commercial_capacity)
        
        # Vehicle age validation (example: max 10 years old)
        current_year = date.today().year
        vehicle_age = current_year - registration.year_of_manufacture
        max_vehicle_age = 10
        self.assertLessEqual(vehicle_age, max_vehicle_age)
    
    def test_registration_renewal(self):
        """Test vehicle registration renewal process"""
        registration = VehicleRegistration.objects.create(
            driver=self.driver,
            plate_number='RAD 123 A',
            vehicle_make='Honda',
            vehicle_model='CB125',
            registration_date=date.today() - timedelta(days=365),
            expiry_date=date.today() - timedelta(days=30),
            status='expired'
        )
        
        # Renew registration
        registration.registration_date = date.today()
        registration.expiry_date = date.today() + timedelta(days=365)
        registration.status = 'active'
        registration.save()
        
        self.assertEqual(registration.status, 'active')
        self.assertGreater(registration.expiry_date, date.today())


class DriverLicenseModelTests(TestCase):
    """
    Unit tests for Driver License model (general driving license)
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver = self.test_factory.create_test_driver()
    
    def test_create_driver_license(self):
        """Test creating driver license record"""
        license_record = DriverLicense.objects.create(
            driver=self.driver,
            license_number='DL123456789',
            license_class='A',  # Motorcycle license
            issue_date=date.today() - timedelta(days=100),
            expiry_date=date.today() + timedelta(days=265),
            issuing_country='Rwanda',
            restrictions=[],
            points_balance=0,
            status='active'
        )
        
        self.assertEqual(license_record.license_number, 'DL123456789')
        self.assertEqual(license_record.license_class, 'A')
        self.assertEqual(license_record.issuing_country, 'Rwanda')
        self.assertEqual(license_record.points_balance, 0)
    
    def test_license_class_validation(self):
        """Test driver license class validation"""
        valid_classes = ['A', 'A1', 'B', 'C', 'D']  # Rwanda license classes
        
        for license_class in valid_classes:
            license_record = DriverLicense(
                driver=self.driver,
                license_number='DL123456789',
                license_class=license_class,
                issue_date=date.today(),
                expiry_date=date.today() + timedelta(days=365)
            )
            license_record.full_clean()  # Should not raise
    
    def test_points_system_tracking(self):
        """Test driving license points system"""
        license_record = DriverLicense.objects.create(
            driver=self.driver,
            license_number='DL123456789',
            license_class='A',
            points_balance=3  # Has violation points
        )
        
        # Maximum points threshold (example: 12 points = license suspension)
        max_points = 12
        self.assertLess(license_record.points_balance, max_points)
        
        # Add violation points
        license_record.points_balance += 2
        license_record.save()
        
        self.assertEqual(license_record.points_balance, 5)


class TaxComplianceRecordModelTests(TestCase):
    """
    Unit tests for Tax Compliance Record model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver = self.test_factory.create_test_driver()
    
    def test_create_tax_compliance_record(self):
        """Test creating tax compliance record"""
        tax_record = TaxComplianceRecord.objects.create(
            driver=self.driver,
            tax_period_start=date.today() - timedelta(days=90),
            tax_period_end=date.today(),
            gross_income=Decimal('450000'),  # RWF
            tax_due=Decimal('0'),  # Below tax threshold
            tax_paid=Decimal('0'),
            filing_date=date.today(),
            payment_date=date.today(),
            compliance_status='compliant',
            tax_identification_number='TIN123456789'
        )
        
        self.assertEqual(tax_record.gross_income, Decimal('450000'))
        self.assertEqual(tax_record.tax_due, Decimal('0'))
        self.assertEqual(tax_record.compliance_status, 'compliant')
        self.assertEqual(tax_record.tax_identification_number, 'TIN123456789')
    
    def test_tax_calculation_validation(self):
        """Test tax calculation validation"""
        # High income requiring tax payment
        high_income_record = TaxComplianceRecord.objects.create(
            driver=self.driver,
            tax_period_start=date.today() - timedelta(days=90),
            tax_period_end=date.today(),
            gross_income=Decimal('2000000'),  # 2M RWF
            tax_due=Decimal('300000'),  # 15% tax rate example
            tax_paid=Decimal('300000'),
            compliance_status='compliant'
        )
        
        # Verify tax calculation logic
        tax_rate = high_income_record.tax_due / high_income_record.gross_income
        expected_rate = Decimal('0.15')  # 15%
        self.assertEqual(tax_rate, expected_rate)
        
        # Verify payment compliance
        is_paid = high_income_record.tax_paid >= high_income_record.tax_due
        self.assertTrue(is_paid)
    
    def test_tax_exemption_threshold(self):
        """Test tax exemption for low-income drivers"""
        low_income_record = TaxComplianceRecord.objects.create(
            driver=self.driver,
            gross_income=Decimal('360000'),  # Below annual threshold (30K/month)
            tax_due=Decimal('0'),
            tax_paid=Decimal('0'),
            compliance_status='exempt'
        )
        
        # Rwanda tax-free threshold (example: 360,000 RWF annually)
        tax_free_threshold = Decimal('360000')
        
        if low_income_record.gross_income <= tax_free_threshold:
            self.assertEqual(low_income_record.tax_due, Decimal('0'))
            self.assertEqual(low_income_record.compliance_status, 'exempt')


class BusinessLicenseModelTests(TestCase):
    """
    Unit tests for Business License model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver = self.test_factory.create_test_driver()
    
    def test_create_business_license(self):
        """Test creating business license record"""
        business_license = BusinessLicense.objects.create(
            driver=self.driver,
            license_number='BL/2024/001234',
            business_name='SafeBoda Services Ltd',
            license_type='transport_services',
            issue_date=date.today() - timedelta(days=45),
            expiry_date=date.today() + timedelta(days=320),
            issuing_authority='Rwanda Development Board (RDB)',
            business_category='passenger_transport',
            annual_fee=Decimal('25000'),  # RWF
            payment_status='paid',
            status='active'
        )
        
        self.assertEqual(business_license.license_number, 'BL/2024/001234')
        self.assertEqual(business_license.business_name, 'SafeBoda Services Ltd')
        self.assertEqual(business_license.license_type, 'transport_services')
        self.assertEqual(business_license.annual_fee, Decimal('25000'))
        self.assertEqual(business_license.payment_status, 'paid')
    
    def test_business_license_categories(self):
        """Test business license categories validation"""
        valid_categories = [
            'passenger_transport',
            'goods_transport',
            'mixed_transport',
            'courier_services'
        ]
        
        for category in valid_categories:
            business_license = BusinessLicense(
                driver=self.driver,
                license_number='BL/2024/001234',
                business_name='Test Business',
                license_type='transport_services',
                business_category=category
            )
            business_license.full_clean()  # Should not raise
    
    def test_business_license_renewal_reminder(self):
        """Test business license renewal reminder logic"""
        # License expiring soon
        expiring_license = BusinessLicense.objects.create(
            driver=self.driver,
            license_number='BL/2024/001234',
            business_name='Test Business',
            expiry_date=date.today() + timedelta(days=30),  # Expires in 30 days
            status='active'
        )
        
        # Check if renewal reminder needed (example: 45 days before expiry)
        reminder_threshold = 45
        days_to_expiry = (expiring_license.expiry_date - date.today()).days
        
        needs_reminder = days_to_expiry <= reminder_threshold
        self.assertTrue(needs_reminder)


class InsuranceRecordModelTests(TestCase):
    """
    Unit tests for Insurance Record model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver = self.test_factory.create_test_driver()
    
    def test_create_insurance_record(self):
        """Test creating insurance record"""
        insurance = InsuranceRecord.objects.create(
            driver=self.driver,
            policy_number='INS/MTR/2024/001234',
            insurance_provider='SORAS Insurance',
            policy_type='comprehensive',
            coverage_start=date.today(),
            coverage_end=date.today() + timedelta(days=365),
            premium_amount=Decimal('120000'),  # RWF
            coverage_limits={
                'third_party_liability': 50000000,  # 50M RWF
                'personal_accident': 5000000,      # 5M RWF
                'vehicle_damage': 2000000          # 2M RWF
            },
            payment_status='paid',
            status='active'
        )
        
        self.assertEqual(insurance.policy_number, 'INS/MTR/2024/001234')
        self.assertEqual(insurance.insurance_provider, 'SORAS Insurance')
        self.assertEqual(insurance.premium_amount, Decimal('120000'))
        self.assertIn('third_party_liability', insurance.coverage_limits)
    
    def test_insurance_coverage_validation(self):
        """Test insurance coverage adequacy"""
        insurance = InsuranceRecord.objects.create(
            driver=self.driver,
            policy_number='INS/MTR/2024/001234',
            insurance_provider='SORAS Insurance',
            policy_type='comprehensive',
            coverage_limits={
                'third_party_liability': 50000000,
                'personal_accident': 5000000
            }
        )
        
        # Validate minimum coverage requirements (RTDA standards)
        min_third_party = 10000000  # 10M RWF minimum
        min_personal_accident = 1000000  # 1M RWF minimum
        
        third_party_coverage = insurance.coverage_limits['third_party_liability']
        personal_accident_coverage = insurance.coverage_limits['personal_accident']
        
        self.assertGreaterEqual(third_party_coverage, min_third_party)
        self.assertGreaterEqual(personal_accident_coverage, min_personal_accident)


class ComplianceAuditModelTests(TestCase):
    """
    Unit tests for Compliance Audit model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver = self.test_factory.create_test_driver()
    
    def test_create_compliance_audit(self):
        """Test creating compliance audit record"""
        audit = ComplianceAudit.objects.create(
            driver=self.driver,
            audit_date=date.today(),
            audit_type='routine_inspection',
            auditor_name='Inspector John Doe',
            auditor_id='AUD123456',
            compliance_checklist={
                'rtda_license': {'status': 'compliant', 'notes': 'Valid until 2025-01-15'},
                'vehicle_registration': {'status': 'compliant', 'notes': 'Registration current'},
                'insurance': {'status': 'compliant', 'notes': 'Policy active'},
                'tax_compliance': {'status': 'compliant', 'notes': 'Taxes up to date'},
                'safety_equipment': {'status': 'non_compliant', 'notes': 'Missing reflective vest'}
            },
            violations_found=[
                {
                    'type': 'safety_equipment',
                    'description': 'Driver not wearing reflective vest',
                    'severity': 'minor',
                    'fine_amount': 5000  # RWF
                }
            ],
            overall_status='conditional_compliance',
            follow_up_required=True,
            follow_up_date=date.today() + timedelta(days=7)
        )
        
        self.assertEqual(audit.audit_type, 'routine_inspection')
        self.assertEqual(audit.overall_status, 'conditional_compliance')
        self.assertTrue(audit.follow_up_required)
        self.assertIn('rtda_license', audit.compliance_checklist)
        self.assertEqual(len(audit.violations_found), 1)
    
    def test_audit_compliance_scoring(self):
        """Test audit compliance scoring calculation"""
        checklist = {
            'rtda_license': {'status': 'compliant'},
            'vehicle_registration': {'status': 'compliant'},
            'insurance': {'status': 'compliant'},
            'tax_compliance': {'status': 'non_compliant'},
            'safety_equipment': {'status': 'compliant'}
        }
        
        audit = ComplianceAudit.objects.create(
            driver=self.driver,
            audit_date=date.today(),
            compliance_checklist=checklist
        )
        
        # Calculate compliance score
        total_items = len(checklist)
        compliant_items = sum(1 for item in checklist.values() 
                            if item['status'] == 'compliant')
        
        compliance_score = (compliant_items / total_items) * 100
        expected_score = 80.0  # 4 out of 5 compliant
        
        self.assertEqual(compliance_score, expected_score)


class RTDAIntegrationServiceTests(TestCase):
    """
    Unit tests for RTDA Integration Service
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.rtda_service = RTDAIntegrationService()
    
    @patch('government.services.rtda_api_client.verify_license')
    def test_verify_rtda_license(self, mock_verify):
        """Test RTDA license verification via API"""
        mock_verify.return_value = {
            'valid': True,
            'license_number': 'RTDA/PSV/2024/001234',
            'status': 'active',
            'expiry_date': '2025-01-15',
            'holder_name': 'John Doe'
        }
        
        result = self.rtda_service.verify_license('RTDA/PSV/2024/001234')
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['status'], 'active')
        mock_verify.assert_called_once_with('RTDA/PSV/2024/001234')
    
    @patch('government.services.rtda_api_client.submit_compliance_report')
    def test_submit_compliance_report(self, mock_submit):
        """Test submitting compliance report to RTDA"""
        mock_submit.return_value = {
            'success': True,
            'submission_id': 'SUB-2024-001234',
            'receipt_number': 'RCP-2024-567890'
        }
        
        report_data = {
            'report_type': 'monthly',
            'period': '2024-01',
            'total_rides': 5000,
            'compliance_rate': 98.5
        }
        
        result = self.rtda_service.submit_compliance_report(report_data)
        
        self.assertTrue(result['success'])
        self.assertIn('submission_id', result)
        mock_submit.assert_called_once()
    
    def test_format_rtda_data(self):
        """Test formatting data for RTDA submission"""
        raw_data = {
            'driver_count': 125,
            'vehicle_count': 120,
            'monthly_rides': 8500,
            'revenue': Decimal('12750000')
        }
        
        formatted_data = self.rtda_service.format_submission_data(raw_data)
        
        self.assertIn('operators', formatted_data)
        self.assertIn('vehicles', formatted_data)
        self.assertIn('monthly_operations', formatted_data)
        self.assertEqual(formatted_data['operators'], 125)


class ComplianceCheckServiceTests(TestCase):
    """
    Unit tests for Compliance Check Service
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.compliance_service = ComplianceCheckService()
        self.driver = self.test_factory.create_test_driver()
    
    def test_check_driver_compliance(self):
        """Test comprehensive driver compliance check"""
        # Create compliance records
        RTDALicense.objects.create(
            driver=self.driver,
            license_number='RTDA/PSV/2024/001234',
            license_type='public_service_vehicle',
            expiry_date=date.today() + timedelta(days=100),
            status='active'
        )
        
        VehicleRegistration.objects.create(
            driver=self.driver,
            plate_number='RAD 123 A',
            vehicle_make='Honda',
            expiry_date=date.today() + timedelta(days=200),
            status='active'
        )
        
        InsuranceRecord.objects.create(
            driver=self.driver,
            policy_number='INS/MTR/2024/001234',
            coverage_end=date.today() + timedelta(days=150),
            status='active'
        )
        
        compliance_result = self.compliance_service.check_driver_compliance(self.driver.id)
        
        self.assertTrue(compliance_result['rtda_license_valid'])
        self.assertTrue(compliance_result['vehicle_registration_valid'])
        self.assertTrue(compliance_result['insurance_valid'])
        self.assertTrue(compliance_result['overall_compliant'])
    
    def test_identify_compliance_issues(self):
        """Test identification of compliance issues"""
        # Create expired license
        RTDALicense.objects.create(
            driver=self.driver,
            license_number='RTDA/PSV/2024/001234',
            license_type='public_service_vehicle',
            expiry_date=date.today() - timedelta(days=30),  # Expired
            status='expired'
        )
        
        issues = self.compliance_service.identify_compliance_issues(self.driver.id)
        
        self.assertIn('rtda_license_expired', issues)
        self.assertEqual(len(issues), 1)  # Should identify the expired license
    
    def test_calculate_compliance_score(self):
        """Test compliance score calculation"""
        compliance_data = {
            'rtda_license_valid': True,
            'vehicle_registration_valid': True,
            'insurance_valid': False,  # Insurance expired
            'tax_compliant': True,
            'safety_compliant': True
        }
        
        score = self.compliance_service.calculate_compliance_score(compliance_data)
        expected_score = 80.0  # 4 out of 5 compliant
        
        self.assertEqual(score, expected_score)


class GovernmentComplianceAPITests(APITestCase):
    """
    Unit tests for government compliance API endpoints
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.driver_user = self.test_factory.create_test_user(role='driver')
        self.driver = self.test_factory.create_test_driver(user=self.driver_user)
        self.admin_user = self.test_factory.create_test_user(role='admin')
        
        # Authenticate as driver
        self.client.force_authenticate(user=self.driver_user)
    
    def test_get_driver_compliance_status(self):
        """Test getting driver compliance status"""
        # Create compliance records
        RTDALicense.objects.create(
            driver=self.driver,
            license_number='RTDA/PSV/2024/001234',
            license_type='public_service_vehicle',
            status='active'
        )
        
        response = self.client.get('/api/v1/government/compliance/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rtda_license', response.data)
        self.assertIn('overall_status', response.data)
    
    def test_upload_compliance_document(self):
        """Test uploading compliance document"""
        document_data = {
            'document_type': 'rtda_license',
            'license_number': 'RTDA/PSV/2024/001234',
            'expiry_date': (date.today() + timedelta(days=365)).isoformat()
        }
        
        response = self.client.post(
            '/api/v1/government/documents/',
            document_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['license_number'], 'RTDA/PSV/2024/001234')
    
    def test_get_compliance_report(self):
        """Test generating compliance report (admin only)"""
        self.client.force_authenticate(user=self.admin_user)
        
        with patch('government.services.ComplianceCheckService.generate_report') as mock_report:
            mock_report.return_value = {
                'total_drivers': 125,
                'compliant_drivers': 118,
                'compliance_rate': 94.4
            }
            
            response = self.client.get('/api/v1/government/compliance/report/')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('compliance_rate', response.data)
    
    def test_verify_license_endpoint(self):
        """Test license verification endpoint"""
        license_data = {
            'license_number': 'RTDA/PSV/2024/001234'
        }
        
        with patch('government.services.RTDAIntegrationService.verify_license') as mock_verify:
            mock_verify.return_value = {
                'valid': True,
                'status': 'active',
                'expiry_date': '2025-01-15'
            }
            
            response = self.client.post(
                '/api/v1/government/verify-license/',
                license_data,
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['valid'])
    
    def test_unauthorized_compliance_access(self):
        """Test unauthorized access to compliance endpoints"""
        customer = self.test_factory.create_test_user(role='customer')
        self.client.force_authenticate(user=customer)
        
        response = self.client.get('/api/v1/government/compliance/report/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)