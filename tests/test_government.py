"""
Test government integration functionality for SafeBoda Rwanda
Comprehensive testing of government APIs and compliance
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock

from government.models import (
    RTDALicense, GovernmentReport, SafetyIncident, TaxRecord, EmergencyContact
)
from government.services import (
    RTDAComplianceService, TaxCalculationService, 
    GovernmentReportingService, EmergencyServicesIntegration
)
from bookings.models import Ride
from authentication.models import DriverProfile

User = get_user_model()


class GovernmentModelsTests(TestCase):
    """Test government integration models"""
    
    def setUp(self):
        """Set up test data"""
        self.driver = User.objects.create_user(
            email='driver@government.test',
            username='driver_gov',
            password='DriverPass123!',
            phone_number='+250788111111',
            national_id='1111111111111111',
            first_name='Test',
            last_name='Driver',
            role='driver'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@government.test',
            username='admin_gov',
            password='AdminPass123!',
            phone_number='+250788222222',
            national_id='2222222222222222',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
    
    def test_rtda_license_creation(self):
        """Test creating RTDA license record"""
        license_record = RTDALicense.objects.create(
            driver=self.driver,
            license_number='RW987654321',
            license_category='B',
            issue_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=365),
            issuing_authority='RTDA Kigali',
            verification_status='verified',
            verification_date=date.today(),
            rtda_response={'status': 'valid', 'driver_name': 'Test Driver'}
        )
        
        self.assertEqual(license_record.driver, self.driver)
        self.assertEqual(license_record.license_number, 'RW987654321')
        self.assertEqual(license_record.verification_status, 'verified')
        self.assertTrue(license_record.is_valid())
    
    def test_government_report_creation(self):
        """Test creating government report"""
        report_data = {
            'total_rides': 1250,
            'total_revenue': 4500000.0,
            'tax_collected': 810000.0,
            'active_drivers': 85,
            'safety_incidents': 2
        }
        
        report = GovernmentReport.objects.create(
            report_type='monthly_summary',
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            report_data=report_data,
            generated_by=self.admin_user,
            status='submitted'
        )
        
        self.assertEqual(report.report_type, 'monthly_summary')
        self.assertEqual(report.report_data['total_rides'], 1250)
        self.assertEqual(report.status, 'submitted')
        self.assertEqual(report.generated_by, self.admin_user)
    
    def test_safety_incident_creation(self):
        """Test creating safety incident"""
        incident = SafetyIncident.objects.create(
            incident_type='accident',
            severity='minor',
            description='Minor collision at intersection',
            location_latitude=Decimal('-1.9441'),
            location_longitude=Decimal('30.0619'),
            location_description='KN 3 Rd & KG 11 Ave intersection',
            district='Gasabo',
            sector='Kimironko',
            reported_by=self.driver,
            incident_date=date.today(),
            status='reported',
            police_case_number='POL-2024-001234',
            emergency_services_contacted=True
        )
        
        self.assertEqual(incident.incident_type, 'accident')
        self.assertEqual(incident.severity, 'minor')
        self.assertEqual(incident.reported_by, self.driver)
        self.assertEqual(incident.status, 'reported')
        self.assertTrue(incident.emergency_services_contacted)
    
    def test_tax_record_creation(self):
        """Test creating tax record"""
        tax_record = TaxRecord.objects.create(
            ride_id='12345',
            gross_amount=Decimal('5000.00'),
            tax_rate=Decimal('18.00'),
            tax_amount=Decimal('900.00'),
            net_amount=Decimal('4100.00'),
            tax_period=date.today().replace(day=1),
            payment_method='mtn_momo',
            rra_reference='RRA-2024-567890',
            status='calculated'
        )
        
        self.assertEqual(tax_record.ride_id, '12345')
        self.assertEqual(float(tax_record.tax_rate), 18.00)
        self.assertEqual(float(tax_record.tax_amount), 900.00)
        self.assertEqual(tax_record.status, 'calculated')
    
    def test_emergency_contact_creation(self):
        """Test creating emergency contact"""
        emergency_contact = EmergencyContact.objects.create(
            service_type='police',
            name='Rwanda National Police - Gasabo',
            phone_number='+250788311110',
            email='gasabo@police.gov.rw',
            address='KG 11 Ave, Kigali',
            district='Gasabo',
            sector='Kimironko',
            is_active=True,
            response_time_minutes=15,
            coordinates_latitude=Decimal('-1.9441'),
            coordinates_longitude=Decimal('30.0619')
        )
        
        self.assertEqual(emergency_contact.service_type, 'police')
        self.assertEqual(emergency_contact.district, 'Gasabo')
        self.assertTrue(emergency_contact.is_active)
        self.assertEqual(emergency_contact.response_time_minutes, 15)


class GovernmentServicesTests(TestCase):
    """Test government integration services"""
    
    def setUp(self):
        """Set up test data"""
        self.driver = User.objects.create_user(
            email='driver@services.test',
            username='driver_services',
            password='DriverPass123!',
            phone_number='+250788333333',
            national_id='3333333333333333',
            first_name='Service',
            last_name='Driver',
            role='driver'
        )
        
        self.customer = User.objects.create_user(
            email='customer@services.test',
            username='customer_services',
            password='CustomerPass123!',
            phone_number='+250788444444',
            national_id='4444444444444444',
            first_name='Service',
            last_name='Customer',
            role='customer'
        )
    
    @patch('government.services.requests.get')
    def test_rtda_license_verification(self, mock_get):
        """Test RTDA license verification service"""
        # Mock successful RTDA API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'valid',
            'license_number': 'RW123456789',
            'driver_name': 'Service Driver',
            'expiry_date': '2025-12-31',
            'category': 'B',
            'restrictions': []
        }
        mock_get.return_value = mock_response
        
        result = RTDAComplianceService.verify_license('RW123456789')
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['license_number'], 'RW123456789')
        self.assertEqual(result['driver_name'], 'Service Driver')
        self.assertEqual(result['category'], 'B')
        mock_get.assert_called_once()
    
    @patch('government.services.requests.get')
    def test_rtda_license_verification_invalid(self, mock_get):
        """Test RTDA license verification for invalid license"""
        # Mock invalid license response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            'status': 'invalid',
            'error': 'License not found'
        }
        mock_get.return_value = mock_response
        
        result = RTDAComplianceService.verify_license('INVALID123')
        
        self.assertFalse(result['is_valid'])
        self.assertIn('error', result)
    
    def test_tax_calculation_service(self):
        """Test tax calculation service"""
        # Test standard VAT calculation
        result = TaxCalculationService.calculate_ride_tax(
            ride_amount=Decimal('5000.00'),
            tax_type='vat'
        )
        
        expected_tax = Decimal('5000.00') * Decimal('0.18')  # 18% VAT
        expected_net = Decimal('5000.00') - expected_tax
        
        self.assertEqual(result['gross_amount'], Decimal('5000.00'))
        self.assertEqual(result['tax_rate'], Decimal('18.00'))
        self.assertEqual(result['tax_amount'], expected_tax)
        self.assertEqual(result['net_amount'], expected_net)
        self.assertEqual(result['tax_type'], 'vat')
    
    def test_tax_calculation_commission(self):
        """Test tax calculation for commission"""
        result = TaxCalculationService.calculate_ride_tax(
            ride_amount=Decimal('10000.00'),
            tax_type='commission_tax'
        )
        
        # Commission tax is typically lower (5%)
        expected_tax = Decimal('10000.00') * Decimal('0.05')
        expected_net = Decimal('10000.00') - expected_tax
        
        self.assertEqual(result['tax_amount'], expected_tax)
        self.assertEqual(result['net_amount'], expected_net)
    
    def test_government_reporting_service(self):
        """Test government reporting service"""
        # Create test data for reporting period
        start_date = date.today().replace(day=1)
        end_date = date.today()
        
        # Create test rides
        for i in range(3):
            Ride.objects.create(
                customer=self.customer,
                driver=self.driver,
                pickup_address=f'Pickup {i}',
                destination_address=f'Destination {i}',
                pickup_latitude=Decimal('-1.9441'),
                pickup_longitude=Decimal('30.0619'),
                destination_latitude=Decimal('-1.9706'),
                destination_longitude=Decimal('30.1044'),
                estimated_distance=Decimal('10.0'),
                estimated_duration=20,
                base_fare=Decimal('1000.00'),
                distance_fare=Decimal('2000.00'),
                total_fare=Decimal('3000.00'),
                payment_method='mtn_momo',
                status='completed'
            )
        
        report_data = GovernmentReportingService.generate_monthly_report(
            start_date, end_date
        )
        
        self.assertEqual(report_data['total_rides'], 3)
        self.assertEqual(float(report_data['total_revenue']), 9000.00)
        self.assertIn('tax_summary', report_data)
        self.assertIn('driver_statistics', report_data)
    
    def test_emergency_services_integration(self):
        """Test emergency services integration"""
        # Create emergency contacts
        EmergencyContact.objects.create(
            service_type='police',
            name='Rwanda National Police',
            phone_number='+250788311110',
            district='Gasabo',
            is_active=True,
            response_time_minutes=10
        )
        
        EmergencyContact.objects.create(
            service_type='medical',
            name='King Faisal Hospital',
            phone_number='+250788311115',
            district='Gasabo',
            is_active=True,
            response_time_minutes=8
        )
        
        # Test finding nearest emergency services
        contacts = EmergencyServicesIntegration.find_nearest_emergency_services(
            latitude=Decimal('-1.9441'),
            longitude=Decimal('30.0619'),
            service_type='police'
        )
        
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]['service_type'], 'police')
        
        # Test getting all emergency services in district
        all_contacts = EmergencyServicesIntegration.get_district_emergency_contacts('Gasabo')
        self.assertEqual(len(all_contacts), 2)
    
    @patch('government.services.requests.post')
    def test_incident_reporting_to_authorities(self, mock_post):
        """Test reporting incident to authorities"""
        # Mock successful reporting response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'received',
            'case_number': 'POL-2024-001234',
            'reference_id': 'REF123456'
        }
        mock_post.return_value = mock_response
        
        incident_data = {
            'type': 'accident',
            'severity': 'minor',
            'location': 'KN 3 Rd & KG 11 Ave',
            'description': 'Minor collision',
            'reporter_id': str(self.driver.id)
        }
        
        result = EmergencyServicesIntegration.report_incident_to_police(incident_data)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['case_number'], 'POL-2024-001234')
        mock_post.assert_called_once()


class GovernmentAPITests(APITestCase):
    """Test government integration API endpoints"""
    
    def setUp(self):
        """Set up test data and authentication"""
        self.admin_user = User.objects.create_user(
            email='admin@government.api',
            username='admin_gov_api',
            password='AdminPass123!',
            phone_number='+250788555555',
            national_id='5555555555555555',
            first_name='Admin',
            last_name='API',
            role='admin'
        )
        
        self.driver = User.objects.create_user(
            email='driver@government.api',
            username='driver_gov_api',
            password='DriverPass123!',
            phone_number='+250788666666',
            national_id='6666666666666666',
            first_name='Driver',
            last_name='API',
            role='driver'
        )
        
        # Get JWT tokens
        admin_refresh = RefreshToken.for_user(self.admin_user)
        self.admin_token = str(admin_refresh.access_token)
        
        driver_refresh = RefreshToken.for_user(self.driver)
        self.driver_token = str(driver_refresh.access_token)
    
    @patch('government.services.RTDAComplianceService.verify_license')
    def test_verify_rtda_license_endpoint(self, mock_verify):
        """Test RTDA license verification endpoint"""
        # Mock verification response
        mock_verify.return_value = {
            'is_valid': True,
            'license_number': 'RW123456789',
            'driver_name': 'Driver API',
            'expiry_date': '2025-12-31',
            'category': 'B'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        url = reverse('government:verify_license')
        data = {'license_number': 'RW123456789'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['data']['is_valid'])
        self.assertEqual(response_data['data']['license_number'], 'RW123456789')
    
    def test_calculate_tax_endpoint(self):
        """Test tax calculation endpoint"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        url = reverse('government:calculate_tax')
        data = {
            'ride_amount': 5000.00,
            'tax_type': 'vat'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])
        self.assertIn('tax_calculation', response_data['data'])
        
        tax_data = response_data['data']['tax_calculation']
        self.assertEqual(float(tax_data['gross_amount']), 5000.00)
        self.assertEqual(float(tax_data['tax_rate']), 18.00)
    
    def test_submit_government_report_endpoint(self):
        """Test government report submission endpoint"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        url = reverse('government:submit_report')
        data = {
            'report_type': 'monthly_summary',
            'period_start': '2024-01-01',
            'period_end': '2024-01-31'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])
        self.assertIn('report_id', response_data['data'])
        
        # Verify report was created in database
        report_id = response_data['data']['report_id']
        report = GovernmentReport.objects.get(id=report_id)
        self.assertEqual(report.report_type, 'monthly_summary')
        self.assertEqual(report.generated_by, self.admin_user)
    
    def test_report_safety_incident_endpoint(self):
        """Test safety incident reporting endpoint"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.driver_token}')
        
        url = reverse('government:report_incident')
        data = {
            'incident_type': 'accident',
            'severity': 'minor',
            'description': 'Minor collision at intersection',
            'location_latitude': -1.9441,
            'location_longitude': 30.0619,
            'location_description': 'KN 3 Rd intersection',
            'district': 'Gasabo',
            'sector': 'Kimironko',
            'emergency_services_contacted': True
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])
        self.assertIn('incident_id', response_data['data'])
        
        # Verify incident was created
        incident_id = response_data['data']['incident_id']
        incident = SafetyIncident.objects.get(id=incident_id)
        self.assertEqual(incident.incident_type, 'accident')
        self.assertEqual(incident.reported_by, self.driver)
    
    def test_get_emergency_contacts_endpoint(self):
        """Test emergency contacts endpoint"""
        # Create test emergency contacts
        EmergencyContact.objects.create(
            service_type='police',
            name='Test Police Station',
            phone_number='+250788311110',
            district='Gasabo',
            is_active=True
        )
        
        EmergencyContact.objects.create(
            service_type='medical',
            name='Test Hospital',
            phone_number='+250788311115',
            district='Gasabo',
            is_active=True
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.driver_token}')
        
        url = reverse('government:emergency_contacts')
        response = self.client.get(url, {'district': 'Gasabo'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['data']['contacts']), 2)
        
        # Check contact structure
        contact = response_data['data']['contacts'][0]
        self.assertIn('service_type', contact)
        self.assertIn('name', contact)
        self.assertIn('phone_number', contact)
    
    def test_get_compliance_status_endpoint(self):
        """Test driver compliance status endpoint"""
        # Create RTDA license for driver
        RTDALicense.objects.create(
            driver=self.driver,
            license_number='RW987654321',
            license_category='B',
            issue_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=365),
            verification_status='verified'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.driver_token}')
        
        url = reverse('government:compliance_status')
        response = self.client.get(url, {'driver_id': str(self.driver.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])
        compliance_data = response_data['data']
        
        self.assertIn('license_status', compliance_data)
        self.assertIn('compliance_score', compliance_data)
        self.assertIn('required_actions', compliance_data)
    
    def test_government_api_authentication_required(self):
        """Test that government endpoints require authentication"""
        url = reverse('government:verify_license')
        data = {'license_number': 'RW123456789'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_government_api_admin_permissions(self):
        """Test that some government endpoints require admin permissions"""
        # Regular driver trying to access admin-only endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.driver_token}')
        
        url = reverse('government:submit_report')
        data = {
            'report_type': 'monthly_summary',
            'period_start': '2024-01-01',
            'period_end': '2024-01-31'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Should be forbidden for non-admin users
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class GovernmentComplianceTests(TestCase):
    """Test government compliance workflows"""
    
    def setUp(self):
        """Set up compliance test data"""
        self.driver = User.objects.create_user(
            email='driver@compliance.test',
            username='driver_compliance',
            password='DriverPass123!',
            phone_number='+250788777777',
            national_id='7777777777777777',
            first_name='Compliance',
            last_name='Driver',
            role='driver'
        )
        
        # Create driver profile
        self.driver_profile = DriverProfile.objects.create(
            user=self.driver,
            license_number='RW123456789',
            license_expiry_date=date.today() + timedelta(days=365),
            license_category='B',
            vehicle_type='motorcycle',
            vehicle_plate_number='RAB 789C',
            vehicle_make='Honda',
            vehicle_model='CB 150',
            vehicle_year=2020,
            vehicle_color='Red',
            insurance_number='INS123456789',
            insurance_expiry_date=date.today() + timedelta(days=365),
            vehicle_inspection_date=date.today() - timedelta(days=30),
            vehicle_inspection_expiry=date.today() + timedelta(days=365)
        )
    
    def test_driver_compliance_check(self):
        """Test comprehensive driver compliance check"""
        # Create valid RTDA license
        RTDALicense.objects.create(
            driver=self.driver,
            license_number='RW123456789',
            license_category='B',
            issue_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=365),
            verification_status='verified'
        )
        
        compliance_status = RTDAComplianceService.check_driver_compliance(self.driver)
        
        self.assertTrue(compliance_status['is_compliant'])
        self.assertEqual(compliance_status['compliance_score'], 100)
        self.assertEqual(len(compliance_status['violations']), 0)
    
    def test_expired_license_compliance(self):
        """Test compliance check with expired license"""
        # Create expired RTDA license
        RTDALicense.objects.create(
            driver=self.driver,
            license_number='RW123456789',
            license_category='B',
            issue_date=date.today() - timedelta(days=730),
            expiry_date=date.today() - timedelta(days=30),  # Expired
            verification_status='expired'
        )
        
        compliance_status = RTDAComplianceService.check_driver_compliance(self.driver)
        
        self.assertFalse(compliance_status['is_compliant'])
        self.assertLess(compliance_status['compliance_score'], 100)
        self.assertGreater(len(compliance_status['violations']), 0)
        
        # Check for specific violation
        violations = compliance_status['violations']
        license_violation = next((v for v in violations if v['type'] == 'expired_license'), None)
        self.assertIsNotNone(license_violation)
    
    def test_tax_compliance_tracking(self):
        """Test tax compliance tracking"""
        # Create tax records
        for i in range(5):
            TaxRecord.objects.create(
                ride_id=f'ride_{i}',
                gross_amount=Decimal('3000.00'),
                tax_rate=Decimal('18.00'),
                tax_amount=Decimal('540.00'),
                net_amount=Decimal('2460.00'),
                tax_period=date.today().replace(day=1),
                status='paid'
            )
        
        compliance_data = TaxCalculationService.get_tax_compliance_report(
            start_date=date.today().replace(day=1),
            end_date=date.today()
        )
        
        self.assertEqual(compliance_data['total_transactions'], 5)
        self.assertEqual(float(compliance_data['total_tax_collected']), 2700.00)
        self.assertEqual(compliance_data['compliance_rate'], 100.0)  # All paid