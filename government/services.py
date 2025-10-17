"""
Government integration services for SafeBoda Rwanda
Handles RTDA compliance, tax calculations, and regulatory reporting
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth import get_user_model

from .models import RTDALicense, GovernmentReport, TaxRecord, SafetyIncident, EmergencyContact
from bookings.models import Ride
from payments.models import Transaction

User = get_user_model()
logger = logging.getLogger(__name__)


class RTDAComplianceService:
    """
    Service for RTDA (Rwanda Transport Development Agency) compliance
    """
    
    def __init__(self):
        self.rtda_api_url = getattr(settings, 'RTDA_API_URL', 'https://api.rtda.gov.rw/v1/')
        self.rtda_api_key = getattr(settings, 'RTDA_API_KEY', 'demo-key')
    
    def verify_driver_license(self, license_number: str, national_id: str) -> Dict[str, Any]:
        """
        Verify driver license with RTDA database
        """
        try:
            # In production, this would make actual API call to RTDA
            verification_data = {
                'license_number': license_number,
                'national_id': national_id,
                'is_valid': True,  # Mock response
                'expiry_date': '2025-12-31',
                'license_class': 'A',
                'restrictions': [],
                'violations': 0,
                'status': 'active'
            }
            
            logger.info(f"RTDA license verification for {license_number}: {verification_data['is_valid']}")
            return verification_data
            
        except Exception as e:
            logger.error(f"RTDA license verification failed: {e}")
            return {
                'license_number': license_number,
                'is_valid': False,
                'error': str(e)
            }
    
    def verify_vehicle_registration(self, plate_number: str) -> Dict[str, Any]:
        """
        Verify vehicle registration with RTDA
        """
        try:
            # Mock vehicle verification
            verification_data = {
                'plate_number': plate_number,
                'is_registered': True,
                'owner_name': 'Vehicle Owner',
                'vehicle_make': 'Honda',
                'vehicle_model': 'CB 125',
                'year': 2023,
                'insurance_valid': True,
                'inspection_due': '2024-06-30',
                'status': 'active'
            }
            
            return verification_data
            
        except Exception as e:
            logger.error(f"Vehicle verification failed: {e}")
            return {
                'plate_number': plate_number,
                'is_registered': False,
                'error': str(e)
            }
    
    def check_compliance_status(self, driver_user_id: int) -> Dict[str, Any]:
        """
        Check overall compliance status for a driver
        """
        try:
            user = User.objects.get(id=driver_user_id)
            
            # Check licenses
            licenses = RTDALicense.objects.filter(holder=user, status='active')
            expired_licenses = [lic for lic in licenses if lic.is_expired]
            
            # Check recent violations/incidents
            recent_incidents = SafetyIncident.objects.filter(
                driver=user,
                incident_datetime__gte=timezone.now() - timedelta(days=180)
            ).count()
            
            compliance_score = 100
            issues = []
            
            if expired_licenses:
                compliance_score -= 30
                issues.append('Expired licenses detected')
            
            if recent_incidents > 3:
                compliance_score -= 20
                issues.append('Multiple recent safety incidents')
            
            compliance_status = {
                'user_id': driver_user_id,
                'compliance_score': max(0, compliance_score),
                'active_licenses': licenses.count(),
                'expired_licenses': len(expired_licenses),
                'recent_incidents': recent_incidents,
                'issues': issues,
                'is_compliant': compliance_score >= 80,
                'last_checked': timezone.now().isoformat()
            }
            
            return compliance_status
            
        except User.DoesNotExist:
            return {
                'user_id': driver_user_id,
                'error': 'Driver not found',
                'is_compliant': False
            }
        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return {
                'user_id': driver_user_id,
                'error': str(e),
                'is_compliant': False
            }


class TaxCalculationService:
    """
    Service for calculating and managing taxes
    """
    
    # Rwanda tax rates (mock values)
    TAX_RATES = {
        'ride_tax': Decimal('0.02'),  # 2% per ride
        'driver_license_fee': Decimal('50000'),  # 50,000 RWF annually
        'vehicle_registration': Decimal('25000'),  # 25,000 RWF annually
        'income_tax': Decimal('0.15'),  # 15% on income above threshold
        'platform_tax': Decimal('0.18'),  # 18% VAT on platform fees
    }
    
    def calculate_ride_tax(self, ride) -> Decimal:
        """
        Calculate tax for a single ride
        """
        try:
            if ride.total_fare:
                tax_amount = ride.total_fare * self.TAX_RATES['ride_tax']
                return tax_amount.quantize(Decimal('0.01'))
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Ride tax calculation failed: {e}")
            return Decimal('0')
    
    def calculate_driver_income_tax(self, driver_user_id: int, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """
        Calculate income tax for a driver over a period
        """
        try:
            # Get all completed rides for the driver in the period
            rides = Ride.objects.filter(
                driver_id=driver_user_id,
                status='completed',
                completed_at__range=[period_start, period_end]
            )
            
            total_earnings = rides.aggregate(
                total=Sum('driver_earnings')
            )['total'] or Decimal('0')
            
            # Rwanda income tax threshold (mock: 360,000 RWF annually)
            annual_threshold = Decimal('360000')
            period_days = (period_end - period_start).days
            period_threshold = annual_threshold * Decimal(period_days) / Decimal('365')
            
            taxable_income = max(Decimal('0'), total_earnings - period_threshold)
            income_tax = taxable_income * self.TAX_RATES['income_tax']
            
            return {
                'driver_user_id': driver_user_id,
                'period_start': period_start,
                'period_end': period_end,
                'total_earnings': total_earnings,
                'taxable_income': taxable_income,
                'income_tax': income_tax.quantize(Decimal('0.01')),
                'tax_rate': self.TAX_RATES['income_tax'],
                'rides_count': rides.count()
            }
            
        except Exception as e:
            logger.error(f"Income tax calculation failed: {e}")
            return {
                'driver_user_id': driver_user_id,
                'error': str(e),
                'income_tax': Decimal('0')
            }
    
    def create_tax_records(self, tax_calculation: Dict[str, Any]) -> Optional[TaxRecord]:
        """
        Create tax record in database
        """
        try:
            if 'error' in tax_calculation:
                return None
            
            tax_record = TaxRecord.objects.create(
                tax_type='income_tax',
                tax_period_start=tax_calculation['period_start'],
                tax_period_end=tax_calculation['period_end'],
                taxpayer_id=tax_calculation['driver_user_id'],
                taxable_amount=tax_calculation['taxable_income'],
                tax_rate_percent=tax_calculation['tax_rate'] * 100,
                tax_amount=tax_calculation['income_tax'],
                status='calculated'
            )
            
            return tax_record
            
        except Exception as e:
            logger.error(f"Tax record creation failed: {e}")
            return None


class GovernmentReportingService:
    """
    Service for generating government compliance reports
    """
    
    def generate_monthly_rides_report(self, year: int, month: int) -> GovernmentReport:
        """
        Generate monthly rides report for government
        """
        try:
            period_start = datetime(year, month, 1)
            if month == 12:
                period_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                period_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            # Collect ride statistics
            rides = Ride.objects.filter(
                created_at__range=[period_start, period_end]
            )
            
            completed_rides = rides.filter(status='completed')
            cancelled_rides = rides.filter(status='cancelled')
            
            report_data = {
                'period': f"{year}-{month:02d}",
                'total_rides': rides.count(),
                'completed_rides': completed_rides.count(),
                'cancelled_rides': cancelled_rides.count(),
                'total_revenue': float(completed_rides.aggregate(
                    total=Sum('total_fare')
                )['total'] or 0),
                'total_distance_km': float(completed_rides.aggregate(
                    total=Sum('distance_km')
                )['total'] or 0),
                'unique_drivers': completed_rides.values('driver').distinct().count(),
                'unique_customers': completed_rides.values('customer').distinct().count(),
                'average_ride_duration_minutes': 0,  # Would calculate from ride data
                'peak_hours': {},  # Would analyze ride time patterns
                'popular_routes': {},  # Would analyze route patterns
            }
            
            summary = f"""
            Monthly Rides Report for {year}-{month:02d}
            
            Total Rides: {report_data['total_rides']:,}
            Completed: {report_data['completed_rides']:,}
            Cancelled: {report_data['cancelled_rides']:,}
            
            Total Revenue: {report_data['total_revenue']:,.2f} RWF
            Total Distance: {report_data['total_distance_km']:,.1f} km
            
            Active Drivers: {report_data['unique_drivers']}
            Active Customers: {report_data['unique_customers']}
            """
            
            report = GovernmentReport.objects.create(
                report_type='monthly_rides',
                title=f"Monthly Rides Report - {year}-{month:02d}",
                period_start=period_start,
                period_end=period_end,
                report_data=report_data,
                summary=summary.strip(),
                status='draft'
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Monthly report generation failed: {e}")
            raise
    
    def generate_tax_collection_report(self, year: int, month: int) -> GovernmentReport:
        """
        Generate tax collection report for government
        """
        try:
            period_start = datetime(year, month, 1)
            if month == 12:
                period_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                period_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            # Collect tax data
            tax_records = TaxRecord.objects.filter(
                tax_period_start__range=[period_start, period_end]
            )
            
            tax_summary = {}
            for tax_type, _ in TaxRecord.TAX_TYPES:
                type_records = tax_records.filter(tax_type=tax_type)
                tax_summary[tax_type] = {
                    'records_count': type_records.count(),
                    'total_taxable_amount': float(type_records.aggregate(
                        total=Sum('taxable_amount')
                    )['total'] or 0),
                    'total_tax_amount': float(type_records.aggregate(
                        total=Sum('tax_amount')
                    )['total'] or 0),
                    'collected_amount': float(type_records.filter(
                        status='collected'
                    ).aggregate(total=Sum('tax_amount'))['total'] or 0),
                    'paid_to_government': float(type_records.filter(
                        status='paid_to_government'
                    ).aggregate(total=Sum('tax_amount'))['total'] or 0),
                }
            
            total_tax_due = sum([data['total_tax_amount'] for data in tax_summary.values()])
            total_collected = sum([data['collected_amount'] for data in tax_summary.values()])
            total_paid = sum([data['paid_to_government'] for data in tax_summary.values()])
            
            report_data = {
                'period': f"{year}-{month:02d}",
                'tax_summary': tax_summary,
                'totals': {
                    'total_tax_due': total_tax_due,
                    'total_collected': total_collected,
                    'total_paid_to_government': total_paid,
                    'collection_rate': (total_collected / total_tax_due * 100) if total_tax_due > 0 else 0,
                    'payment_rate': (total_paid / total_tax_due * 100) if total_tax_due > 0 else 0,
                }
            }
            
            summary = f"""
            Tax Collection Report for {year}-{month:02d}
            
            Total Tax Due: {total_tax_due:,.2f} RWF
            Total Collected: {total_collected:,.2f} RWF
            Total Paid to Government: {total_paid:,.2f} RWF
            
            Collection Rate: {report_data['totals']['collection_rate']:.1f}%
            Payment Rate: {report_data['totals']['payment_rate']:.1f}%
            """
            
            report = GovernmentReport.objects.create(
                report_type='tax_collection',
                title=f"Tax Collection Report - {year}-{month:02d}",
                period_start=period_start,
                period_end=period_end,
                report_data=report_data,
                summary=summary.strip(),
                status='draft'
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Tax collection report generation failed: {e}")
            raise


class EmergencyServicesIntegration:
    """
    Integration with Rwanda emergency services
    """
    
    def __init__(self):
        self.emergency_api_url = getattr(settings, 'EMERGENCY_API_URL', 'https://emergency.gov.rw/api/')
        self.emergency_api_key = getattr(settings, 'EMERGENCY_API_KEY', 'demo-key')
    
    def report_emergency_incident(self, incident: SafetyIncident) -> Dict[str, Any]:
        """
        Report safety incident to emergency services
        """
        try:
            incident_data = {
                'incident_id': str(incident.id),
                'incident_type': incident.incident_type,
                'severity': incident.severity,
                'location': {
                    'latitude': incident.location_latitude,
                    'longitude': incident.location_longitude,
                    'address': incident.location_address,
                },
                'description': incident.description,
                'datetime': incident.incident_datetime.isoformat(),
                'contacts': {
                    'driver_phone': incident.driver.phone_number if incident.driver else None,
                    'customer_phone': incident.customer.phone_number if incident.customer else None,
                },
                'platform': 'SafeBoda Rwanda'
            }
            
            # In production, would make actual API call
            response_data = {
                'emergency_case_id': f"EMG{incident.id}",
                'status': 'received',
                'response_eta_minutes': 15,
                'assigned_unit': 'Police Unit 247',
                'contact_number': '+250788123456'
            }
            
            logger.info(f"Emergency incident reported: {incident.id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Emergency reporting failed: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def get_nearest_emergency_services(self, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """
        Get nearest emergency services to a location
        """
        try:
            # In production, would query actual emergency services database
            services = EmergencyContact.objects.filter(is_active=True)
            
            nearest_services = []
            for service in services:
                nearest_services.append({
                    'type': service.contact_type,
                    'name': service.name,
                    'phone': service.phone_number,
                    'emergency_number': service.emergency_number,
                    'response_time_minutes': service.response_time_minutes,
                    'distance_km': 5.0,  # Mock distance calculation
                })
            
            return sorted(nearest_services, key=lambda x: x['response_time_minutes'])
            
        except Exception as e:
            logger.error(f"Emergency services lookup failed: {e}")
            return []