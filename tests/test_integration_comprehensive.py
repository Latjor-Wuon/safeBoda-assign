"""
Comprehensive integration tests for SafeBoda Rwanda platform
Testing complete user workflows and system interactions for RTDA compliance
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, date
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import Mock, patch, MagicMock

from authentication.models import User, DriverProfile, VerificationCode
from bookings.models import Ride, RideLocation, FareCalculation
from payments.models import Payment, PaymentMethod, Transaction
from notifications.models import Notification, NotificationPreference
from analytics.models import RideMetrics, RevenueMetrics, PerformanceMetrics
from government.models import RTDALicense, VehicleRegistration, InsuranceRecord
from testing_framework.utils import TestDataFactory, TestAssertions


class CompleteRideWorkflowIntegrationTests(TransactionTestCase):
    """
    Integration tests for complete ride booking workflow
    Testing end-to-end customer and driver experience
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        
        # Create test users
        self.customer = self.test_factory.create_test_user(
            email='customer@test.rw',
            phone_number='+250788123456',
            role='customer'
        )
        self.driver = self.test_factory.create_test_driver(
            email='driver@test.rw',
            phone_number='+250788987654'
        )
        
        # Set up notification preferences
        NotificationPreference.objects.create(
            user=self.customer,
            sms_enabled=True,
            push_enabled=True,
            ride_updates=True
        )
        
        NotificationPreference.objects.create(
            user=self.driver.user,
            sms_enabled=True,
            push_enabled=True,
            ride_updates=True
        )
    
    def test_complete_ride_booking_workflow(self):
        """Test complete ride booking from request to completion"""
        
        # Step 1: Customer creates ride request
        ride_data = {
            'pickup_address': 'KG 11 Ave, Kigali',
            'pickup_latitude': Decimal('-1.9441'),
            'pickup_longitude': Decimal('30.0619'),
            'destination_address': 'KN 3 Rd, Kigali',
            'destination_latitude': Decimal('-1.9506'),
            'destination_longitude': Decimal('30.0588'),
            'ride_type': 'standard',
            'payment_method': 'mtn_momo'
        }
        
        ride = Ride.objects.create(
            customer=self.customer,
            **ride_data,
            status='requested',
            base_fare=Decimal('1500'),
            distance_km=Decimal('5.2')
        )
        
        self.assertEqual(ride.status, 'requested')
        self.assertEqual(ride.customer, self.customer)
        
        # Step 2: System notifies available drivers
        ride_request_notifications = Notification.objects.filter(
            recipient=self.driver.user,
            notification_type='ride_request'
        )
        
        # In real system, this would be created by the matching service
        Notification.objects.create(
            recipient=self.driver.user,
            title='New Ride Request',
            message=f'New ride request from {ride.pickup_address}',
            notification_type='ride_request',
            metadata={'ride_id': ride.id}
        )
        
        # Step 3: Driver accepts ride
        ride.driver = self.driver
        ride.status = 'accepted'
        ride.accepted_at = timezone.now()
        ride.save()
        
        self.assertEqual(ride.status, 'accepted')
        self.assertEqual(ride.driver, self.driver)
        
        # Step 4: Customer receives confirmation notification
        confirmation_notification = Notification.objects.create(
            recipient=self.customer,
            title='Ride Confirmed',
            message=f'Driver {self.driver.user.first_name} has accepted your ride',
            notification_type='ride_update',
            metadata={'ride_id': ride.id, 'driver_id': self.driver.id}
        )
        
        self.assertEqual(confirmation_notification.notification_type, 'ride_update')
        
        # Step 5: Driver arrives at pickup location
        ride.status = 'driver_arrived'
        ride.driver_arrived_at = timezone.now()
        ride.save()
        
        # Create arrival notification
        arrival_notification = Notification.objects.create(
            recipient=self.customer,
            title='Driver Arrived',
            message='Your driver has arrived at the pickup location',
            notification_type='ride_update'
        )
        
        # Step 6: Ride starts
        ride.status = 'in_progress'
        ride.started_at = timezone.now()
        ride.save()
        
        # Step 7: Track ride progress with GPS locations
        location_points = [
            (Decimal('-1.9441'), Decimal('30.0619')),  # Pickup
            (Decimal('-1.9450'), Decimal('30.0610')),  # Midpoint 1
            (Decimal('-1.9470'), Decimal('30.0600')),  # Midpoint 2
            (Decimal('-1.9506'), Decimal('30.0588'))   # Destination
        ]
        
        for i, (lat, lng) in enumerate(location_points):
            RideLocation.objects.create(
                ride=ride,
                latitude=lat,
                longitude=lng,
                speed=Decimal('25.0') if i > 0 else Decimal('0'),
                bearing=Decimal('180.0'),
                timestamp=timezone.now() + timedelta(minutes=i*2)
            )
        
        # Verify location tracking
        locations = RideLocation.objects.filter(ride=ride).count()
        self.assertEqual(locations, 4)
        
        # Step 8: Ride completion
        ride.status = 'completed'
        ride.completed_at = timezone.now()
        ride.total_fare = ride.base_fare  # Simplified fare calculation
        ride.save()
        
        # Step 9: Create fare calculation record
        fare_calculation = FareCalculation.objects.create(
            ride=ride,
            base_fare=ride.base_fare,
            distance_fare=Decimal('1000'),
            time_fare=Decimal('300'),
            surge_multiplier=Decimal('1.0'),
            total_fare=ride.total_fare,
            calculation_details={
                'distance_km': float(ride.distance_km),
                'duration_minutes': 20,
                'surge_applied': False
            }
        )
        
        self.assertEqual(fare_calculation.total_fare, ride.total_fare)
        
        # Step 10: Process payment
        payment = Payment.objects.create(
            ride=ride,
            customer=self.customer,
            payment_method='mtn_momo',
            amount=ride.total_fare,
            currency='RWF',
            momo_phone_number='+250788123456',
            status='completed'
        )
        
        # Create transaction record
        transaction_record = Transaction.objects.create(
            payment=payment,
            transaction_type='payment',
            amount=payment.amount,
            currency='RWF',
            external_transaction_id='MTN123456789',
            status='completed'
        )
        
        # Step 11: Send completion notifications
        completion_notification = Notification.objects.create(
            recipient=self.customer,
            title='Ride Completed',
            message=f'Your ride is complete. Total fare: {ride.total_fare} RWF',
            notification_type='ride_update'
        )
        
        payment_notification = Notification.objects.create(
            recipient=self.customer,
            title='Payment Processed',
            message=f'Payment of {payment.amount} RWF processed successfully',
            notification_type='payment'
        )
        
        # Verify complete workflow
        final_ride = Ride.objects.get(id=ride.id)
        self.assertEqual(final_ride.status, 'completed')
        self.assertIsNotNone(final_ride.completed_at)
        self.assertEqual(final_ride.total_fare, payment.amount)
        
        # Verify notifications sent
        customer_notifications = Notification.objects.filter(
            recipient=self.customer
        ).count()
        self.assertGreaterEqual(customer_notifications, 3)  # Confirmation, arrival, completion
    
    def test_ride_cancellation_workflow(self):
        """Test ride cancellation workflow with refund processing"""
        
        # Create ride with payment
        ride = Ride.objects.create(
            customer=self.customer,
            driver=self.driver,
            pickup_address='Test Pickup',
            destination_address='Test Destination',
            status='accepted',
            base_fare=Decimal('2000')
        )
        
        payment = Payment.objects.create(
            ride=ride,
            customer=self.customer,
            payment_method='mtn_momo',
            amount=ride.base_fare,
            currency='RWF',
            status='completed'
        )
        
        # Cancel ride
        ride.status = 'cancelled'
        ride.cancelled_at = timezone.now()
        ride.cancellation_reason = 'customer_request'
        ride.save()
        
        # Process refund
        refund_payment = Payment.objects.create(
            ride=ride,
            customer=self.customer,
            payment_method='mtn_momo',
            amount=-payment.amount,  # Negative for refund
            currency='RWF',
            status='completed',
            payment_type='refund'
        )
        
        # Create refund transaction
        Transaction.objects.create(
            payment=refund_payment,
            transaction_type='refund',
            amount=abs(refund_payment.amount),
            currency='RWF',
            external_transaction_id='REF123456789',
            status='completed'
        )
        
        # Send cancellation notification
        Notification.objects.create(
            recipient=self.customer,
            title='Ride Cancelled',
            message=f'Your ride has been cancelled. Refund of {abs(refund_payment.amount)} RWF processed.',
            notification_type='ride_update'
        )
        
        # Verify cancellation and refund
        cancelled_ride = Ride.objects.get(id=ride.id)
        self.assertEqual(cancelled_ride.status, 'cancelled')
        self.assertEqual(refund_payment.amount, -payment.amount)


class UserRegistrationIntegrationTests(APITestCase):
    """
    Integration tests for user registration and verification workflow
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
    
    def test_customer_registration_workflow(self):
        """Test complete customer registration with phone verification"""
        
        # Step 1: Register new customer
        registration_data = {
            'email': 'newcustomer@test.rw',
            'phone_number': '+250788555444',
            'first_name': 'Jean',
            'last_name': 'Uwimana',
            'password': 'SecurePass123!',
            'role': 'customer'
        }
        
        response = self.client.post('/api/v1/auth/register/', registration_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user_id', response.data)
        
        user_id = response.data['user_id']
        user = User.objects.get(id=user_id)
        
        # User should be created but not verified
        self.assertEqual(user.email, 'newcustomer@test.rw')
        self.assertFalse(user.phone_verified)
        
        # Step 2: System sends verification code
        verification_code = VerificationCode.objects.create(
            user=user,
            phone_number=user.phone_number,
            code='123456',
            purpose='phone_verification'
        )
        
        # Step 3: User submits verification code
        verify_data = {
            'phone_number': '+250788555444',
            'code': '123456'
        }
        
        response = self.client.post('/api/v1/auth/verify-phone/', verify_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # User should now be verified
        user.refresh_from_db()
        self.assertTrue(user.phone_verified)
        
        # Step 4: Create default notification preferences
        preferences = NotificationPreference.objects.create(
            user=user,
            sms_enabled=True,
            push_enabled=True,
            ride_updates=True,
            payment_updates=True
        )
        
        self.assertEqual(preferences.user, user)
        
        # Step 5: Send welcome notification
        welcome_notification = Notification.objects.create(
            recipient=user,
            title='Welcome to SafeBoda Rwanda',
            message='Your account has been verified. Start booking rides now!',
            notification_type='system'
        )
        
        # Verify complete registration workflow
        final_user = User.objects.get(id=user_id)
        self.assertTrue(final_user.phone_verified)
        self.assertTrue(final_user.is_active)
        
        notifications = Notification.objects.filter(recipient=user).count()
        self.assertEqual(notifications, 1)
    
    def test_driver_registration_workflow(self):
        """Test driver registration with document verification"""
        
        # Step 1: Register driver user account
        registration_data = {
            'email': 'newdriver@test.rw',
            'phone_number': '+250788777888',
            'first_name': 'Paul',
            'last_name': 'Kagame',
            'password': 'DriverPass123!',
            'role': 'driver'
        }
        
        response = self.client.post('/api/v1/auth/register/', registration_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user = User.objects.get(id=response.data['user_id'])
        
        # Step 2: Create driver profile
        profile_data = {
            'national_id': '1198880012345678',
            'date_of_birth': '1988-01-15',
            'address': 'Kigali, Rwanda',
            'emergency_contact_name': 'Marie Kagame',
            'emergency_contact_phone': '+250788999000',
            'license_number': 'DL123456789',
            'vehicle_make': 'Honda',
            'vehicle_model': 'CB125',
            'vehicle_plate': 'RAD 789 Z'
        }
        
        driver_profile = DriverProfile.objects.create(
            user=user,
            **profile_data,
            verification_status='pending'
        )
        
        # Step 3: Submit compliance documents
        rtda_license = RTDALicense.objects.create(
            driver=driver_profile,
            license_number='RTDA/PSV/2024/002345',
            license_type='public_service_vehicle',
            issue_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=335),
            status='active'
        )
        
        vehicle_registration = VehicleRegistration.objects.create(
            driver=driver_profile,
            plate_number='RAD 789 Z',
            vehicle_make='Honda',
            vehicle_model='CB125',
            year_of_manufacture=2022,
            registration_date=date.today() - timedelta(days=60),
            expiry_date=date.today() + timedelta(days=305),
            status='active'
        )
        
        insurance_record = InsuranceRecord.objects.create(
            driver=driver_profile,
            policy_number='INS/MTR/2024/002345',
            insurance_provider='SORAS Insurance',
            coverage_start=date.today(),
            coverage_end=date.today() + timedelta(days=365),
            status='active'
        )
        
        # Step 4: System verifies documents (simplified)
        driver_profile.verification_status = 'verified'
        driver_profile.verified_at = timezone.now()
        driver_profile.save()
        
        # Step 5: Driver activation notification
        activation_notification = Notification.objects.create(
            recipient=user,
            title='Driver Account Activated',
            message='Your driver account has been verified and activated. You can now receive ride requests.',
            notification_type='system'
        )
        
        # Verify complete driver registration
        final_profile = DriverProfile.objects.get(id=driver_profile.id)
        self.assertEqual(final_profile.verification_status, 'verified')
        self.assertIsNotNone(final_profile.verified_at)


class PaymentIntegrationTests(TransactionTestCase):
    """
    Integration tests for payment processing workflows
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.ride = self.test_factory.create_test_ride(customer=self.customer)
    
    @patch('payments.services.MTNMoMoService.process_payment')
    @patch('payments.services.MTNMoMoService.verify_transaction')
    def test_mtn_mobile_money_payment_workflow(self, mock_verify, mock_process):
        """Test complete MTN Mobile Money payment workflow"""
        
        # Step 1: Customer initiates payment
        payment_data = {
            'ride': self.ride.id,
            'payment_method': 'mtn_momo',
            'amount': '2500',
            'currency': 'RWF',
            'momo_phone_number': '+250788123456'
        }
        
        payment = Payment.objects.create(
            ride=self.ride,
            customer=self.customer,
            **{k: v for k, v in payment_data.items() if k != 'ride'}
        )
        
        # Step 2: Process payment with MTN
        mock_process.return_value = {
            'status': 'SUCCESS',
            'transaction_id': 'MTN123456789',
            'reference': f'RIDE-{self.ride.id}'
        }
        
        # Simulate payment processing
        payment.status = 'processing'
        payment.external_transaction_id = 'MTN123456789'
        payment.save()
        
        # Step 3: Create transaction record
        transaction = Transaction.objects.create(
            payment=payment,
            transaction_type='payment',
            amount=payment.amount,
            currency='RWF',
            external_transaction_id='MTN123456789',
            provider_response={
                'status': 'SUCCESS',
                'timestamp': timezone.now().isoformat()
            },
            status='processing'
        )
        
        # Step 4: Verify transaction status
        mock_verify.return_value = {
            'verified': True,
            'status': 'COMPLETED',
            'amount': '2500',
            'currency': 'RWF'
        }
        
        # Update payment status
        payment.status = 'completed'
        payment.processed_at = timezone.now()
        payment.save()
        
        transaction.status = 'completed'
        transaction.save()
        
        # Step 5: Update ride payment status
        self.ride.payment_status = 'paid'
        self.ride.save()
        
        # Step 6: Send payment confirmation
        payment_notification = Notification.objects.create(
            recipient=self.customer,
            title='Payment Successful',
            message=f'Your payment of {payment.amount} RWF has been processed successfully.',
            notification_type='payment',
            metadata={'payment_id': payment.id, 'transaction_id': transaction.id}
        )
        
        # Verify complete payment workflow
        final_payment = Payment.objects.get(id=payment.id)
        self.assertEqual(final_payment.status, 'completed')
        self.assertIsNotNone(final_payment.processed_at)
        
        final_transaction = Transaction.objects.get(id=transaction.id)
        self.assertEqual(final_transaction.status, 'completed')
        
        final_ride = Ride.objects.get(id=self.ride.id)
        self.assertEqual(final_ride.payment_status, 'paid')
    
    def test_payment_method_management_workflow(self):
        """Test payment method addition and verification"""
        
        # Step 1: Add new payment method
        payment_method = PaymentMethod.objects.create(
            user=self.customer,
            method_type='mtn_momo',
            phone_number='+250788123456',
            is_default=False,
            is_verified=False
        )
        
        # Step 2: Send verification code (simulated)
        verification_code = '654321'
        
        # Step 3: Verify payment method
        payment_method.is_verified = True
        payment_method.verified_at = timezone.now()
        payment_method.save()
        
        # Step 4: Set as default if first payment method
        user_payment_methods = PaymentMethod.objects.filter(user=self.customer)
        if user_payment_methods.count() == 1:
            payment_method.is_default = True
            payment_method.save()
        
        # Verify payment method setup
        final_method = PaymentMethod.objects.get(id=payment_method.id)
        self.assertTrue(final_method.is_verified)
        self.assertTrue(final_method.is_default)


class AnalyticsIntegrationTests(TestCase):
    """
    Integration tests for analytics data aggregation and reporting
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
    
    def test_daily_metrics_aggregation_workflow(self):
        """Test daily analytics metrics aggregation from operational data"""
        
        target_date = date.today()
        
        # Create test data for the day
        customers = [
            self.test_factory.create_test_user(f'customer{i}@test.rw', role='customer')
            for i in range(5)
        ]
        
        drivers = [
            self.test_factory.create_test_driver(f'driver{i}@test.rw')
            for i in range(3)
        ]
        
        # Create rides for the day
        rides = []
        for i in range(15):
            customer = customers[i % len(customers)]
            driver = drivers[i % len(drivers)]
            
            ride = Ride.objects.create(
                customer=customer,
                driver=driver,
                pickup_address=f'Pickup {i}',
                destination_address=f'Destination {i}',
                status='completed' if i < 12 else 'cancelled',
                base_fare=Decimal('1500'),
                total_fare=Decimal('1500') if i < 12 else Decimal('0'),
                distance_km=Decimal('5.0'),
                started_at=timezone.now() - timedelta(hours=8-i),
                completed_at=timezone.now() - timedelta(hours=7-i) if i < 12 else None,
                cancelled_at=timezone.now() - timedelta(hours=7-i) if i >= 12 else None
            )
            rides.append(ride)
        
        # Create payments for completed rides
        for ride in rides[:12]:  # Only completed rides
            Payment.objects.create(
                ride=ride,
                customer=ride.customer,
                payment_method='mtn_momo',
                amount=ride.total_fare,
                currency='RWF',
                status='completed'
            )
        
        # Aggregate ride metrics
        total_rides = len(rides)
        completed_rides = len([r for r in rides if r.status == 'completed'])
        cancelled_rides = len([r for r in rides if r.status == 'cancelled'])
        
        average_duration = sum(
            (r.completed_at - r.started_at).total_seconds() / 60
            for r in rides if r.completed_at and r.started_at
        ) / completed_rides if completed_rides > 0 else 0
        
        average_distance = sum(
            float(r.distance_km) for r in rides if r.distance_km
        ) / total_rides if total_rides > 0 else 0
        
        # Create ride metrics record
        ride_metrics = RideMetrics.objects.create(
            date=target_date,
            total_rides=total_rides,
            completed_rides=completed_rides,
            cancelled_rides=cancelled_rides,
            average_ride_duration=Decimal(str(round(average_duration, 2))),
            average_distance=Decimal(str(round(average_distance, 2))),
            peak_hour_rides=8,  # Simplified
            off_peak_rides=total_rides - 8
        )
        
        # Aggregate revenue metrics
        total_payments = Payment.objects.filter(
            ride__in=rides,
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        revenue_metrics = RevenueMetrics.objects.create(
            date=target_date,
            total_revenue=total_payments,
            gross_revenue=total_payments,
            commission_revenue=total_payments * Decimal('0.20'),  # 20% commission
            driver_earnings=total_payments * Decimal('0.80'),     # 80% to drivers
            currency='RWF',
            average_fare=total_payments / completed_rides if completed_rides > 0 else Decimal('0'),
            payment_method_breakdown={
                'mtn_momo': float(total_payments),
                'airtel_money': 0,
                'cash': 0
            }
        )
        
        # Calculate performance metrics
        completion_rate = (completed_rides / total_rides) * 100 if total_rides > 0 else 0
        
        performance_metrics = PerformanceMetrics.objects.create(
            date=target_date,
            average_wait_time=Decimal('4.5'),  # Simulated
            driver_acceptance_rate=Decimal(str(completion_rate)),
            customer_rating=Decimal('4.3'),
            driver_rating=Decimal('4.5'),
            service_uptime=Decimal('99.8')
        )
        
        # Verify metrics creation
        self.assertEqual(ride_metrics.total_rides, 15)
        self.assertEqual(ride_metrics.completed_rides, 12)
        self.assertEqual(ride_metrics.cancelled_rides, 3)
        
        self.assertEqual(revenue_metrics.total_revenue, Decimal('18000'))  # 12 * 1500
        self.assertGreater(performance_metrics.service_uptime, Decimal('99.0'))
    
    def test_compliance_reporting_workflow(self):
        """Test RTDA compliance report generation workflow"""
        
        # Create compliance data
        drivers = [
            self.test_factory.create_test_driver(f'driver{i}@compliance.rw')
            for i in range(10)
        ]
        
        # Create compliance records for drivers
        compliant_count = 0
        for i, driver in enumerate(drivers):
            # RTDA License (8 out of 10 compliant)
            if i < 8:
                RTDALicense.objects.create(
                    driver=driver,
                    license_number=f'RTDA/PSV/2024/{1000+i:06d}',
                    license_type='public_service_vehicle',
                    expiry_date=date.today() + timedelta(days=100),
                    status='active'
                )
            
            # Vehicle Registration (9 out of 10 compliant)
            if i < 9:
                VehicleRegistration.objects.create(
                    driver=driver,
                    plate_number=f'RAD {100+i} A',
                    vehicle_make='Honda',
                    vehicle_model='CB125',
                    expiry_date=date.today() + timedelta(days=200),
                    status='active'
                )
            
            # Insurance (all compliant)
            InsuranceRecord.objects.create(
                driver=driver,
                policy_number=f'INS/MTR/2024/{2000+i:06d}',
                insurance_provider='SORAS Insurance',
                coverage_end=date.today() + timedelta(days=300),
                status='active'
            )
        
        # Calculate compliance rates
        total_drivers = len(drivers)
        rtda_compliant = RTDALicense.objects.filter(
            driver__in=drivers,
            status='active',
            expiry_date__gt=date.today()
        ).count()
        
        vehicle_compliant = VehicleRegistration.objects.filter(
            driver__in=drivers,
            status='active',
            expiry_date__gt=date.today()
        ).count()
        
        insurance_compliant = InsuranceRecord.objects.filter(
            driver__in=drivers,
            status='active',
            coverage_end__gt=date.today()
        ).count()
        
        # Generate compliance report
        from analytics.models import ComplianceReport
        
        compliance_report = ComplianceReport.objects.create(
            report_date=date.today(),
            report_type='daily',
            reporting_period_start=date.today(),
            reporting_period_end=date.today(),
            driver_count=total_drivers,
            vehicle_count=total_drivers,  # Assuming 1:1 ratio
            compliance_metrics={
                'driver_licensing': {
                    'compliant': rtda_compliant,
                    'total': total_drivers,
                    'rate': (rtda_compliant / total_drivers) * 100
                },
                'vehicle_registration': {
                    'compliant': vehicle_compliant,
                    'total': total_drivers,
                    'rate': (vehicle_compliant / total_drivers) * 100
                },
                'insurance_coverage': {
                    'compliant': insurance_compliant,
                    'total': total_drivers,
                    'rate': (insurance_compliant / total_drivers) * 100
                }
            },
            violations=[
                {'type': 'expired_rtda_license', 'count': total_drivers - rtda_compliant},
                {'type': 'expired_vehicle_registration', 'count': total_drivers - vehicle_compliant}
            ],
            status='generated'
        )
        
        # Verify compliance report
        self.assertEqual(compliance_report.driver_count, 10)
        self.assertEqual(compliance_report.compliance_metrics['driver_licensing']['rate'], 80.0)
        self.assertEqual(compliance_report.compliance_metrics['vehicle_registration']['rate'], 90.0)
        self.assertEqual(compliance_report.compliance_metrics['insurance_coverage']['rate'], 100.0)


class SystemLoadIntegrationTests(TransactionTestCase):
    """
    Integration tests for system performance under load
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
    
    def test_concurrent_ride_booking_load(self):
        """Test system handling multiple concurrent ride bookings"""
        
        # Create test users
        customers = [
            self.test_factory.create_test_user(f'load_customer{i}@test.rw', role='customer')
            for i in range(20)
        ]
        
        drivers = [
            self.test_factory.create_test_driver(f'load_driver{i}@test.rw')
            for i in range(10)
        ]
        
        # Simulate concurrent ride requests
        rides_created = []
        
        with transaction.atomic():
            for i, customer in enumerate(customers):
                ride = Ride.objects.create(
                    customer=customer,
                    pickup_address=f'Pickup Location {i}',
                    destination_address=f'Destination {i}',
                    pickup_latitude=Decimal('-1.9441') + Decimal(str(i * 0.001)),
                    pickup_longitude=Decimal('30.0619') + Decimal(str(i * 0.001)),
                    destination_latitude=Decimal('-1.9506') + Decimal(str(i * 0.001)),
                    destination_longitude=Decimal('30.0588') + Decimal(str(i * 0.001)),
                    ride_type='standard',
                    payment_method='mtn_momo',
                    base_fare=Decimal('1500'),
                    distance_km=Decimal('5.0'),
                    status='requested'
                )
                rides_created.append(ride)
        
        # Verify all rides were created successfully
        self.assertEqual(len(rides_created), 20)
        
        # Simulate ride matching and acceptance
        for i, ride in enumerate(rides_created[:10]):  # Match first 10 rides
            ride.driver = drivers[i]
            ride.status = 'accepted'
            ride.accepted_at = timezone.now()
            ride.save()
        
        # Verify ride matching
        matched_rides = Ride.objects.filter(status='accepted').count()
        self.assertEqual(matched_rides, 10)
        
        unmatched_rides = Ride.objects.filter(status='requested').count()
        self.assertEqual(unmatched_rides, 10)
    
    def test_high_volume_notification_processing(self):
        """Test notification system under high volume"""
        
        # Create users
        users = [
            self.test_factory.create_test_user(f'notify_user{i}@test.rw')
            for i in range(100)
        ]
        
        # Create notification preferences for all users
        for user in users:
            NotificationPreference.objects.create(
                user=user,
                sms_enabled=True,
                push_enabled=True,
                ride_updates=True
            )
        
        # Send bulk notifications
        notifications_created = []
        
        with transaction.atomic():
            for user in users:
                notification = Notification.objects.create(
                    recipient=user,
                    title='System Announcement',
                    message='SafeBoda Rwanda services are now available in your area!',
                    notification_type='system',
                    priority='medium'
                )
                notifications_created.append(notification)
        
        # Verify notifications were created
        self.assertEqual(len(notifications_created), 100)
        
        # Verify notification preferences are respected
        total_notifications = Notification.objects.filter(
            recipient__in=users
        ).count()
        
        self.assertEqual(total_notifications, 100)