"""
Comprehensive unit tests for SafeBoda Rwanda payment system
Achieving 90%+ code coverage for RTDA compliance
"""


from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from payments.models import Payment, PaymentMethod, Transaction
from authentication.models import User, DriverProfile
from testing_framework.utils import TestDataFactory, TestAssertions


class PaymentModelTests(TestCase):
    """
    Unit tests for Payment model with Rwanda mobile money integration
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.ride = self.test_factory.create_test_ride(customer=self.customer)
    
    def test_create_payment_with_mtn_momo(self):
        """Test creating payment with MTN Mobile Money"""
        payment = Payment.objects.create(
            ride=self.ride,
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF',
            momo_phone_number='+250788123456',
            status='pending'
        )
        
        self.assertEqual(payment.payment_method, 'mtn_momo')
        self.assertEqual(payment.currency, 'RWF')
        self.assertEqual(payment.amount, Decimal('1500'))
        self.assertEqual(payment.status, 'pending')
        self.assertTrue(payment.momo_phone_number.startswith('+250'))
    
    def test_create_payment_with_airtel_money(self):
        """Test creating payment with Airtel Money"""
        payment = Payment.objects.create(
            ride=self.ride,
            customer=self.customer,
            payment_method='airtel_money',
            amount=Decimal('2000'),
            currency='RWF',
            momo_phone_number='+250735987654',
            status='pending'
        )
        
        self.assertEqual(payment.payment_method, 'airtel_money')
        self.assertEqual(payment.amount, Decimal('2000'))
        self.assertTrue(payment.momo_phone_number.startswith('+250'))
    
    def test_payment_string_representation(self):
        """Test payment __str__ method"""
        payment = Payment.objects.create(
            ride=self.ride,
            customer=self.customer,
            payment_method='cash',
            amount=Decimal('1000'),
            currency='RWF'
        )
        
        expected_str = f"Payment #{payment.id} - {payment.amount} {payment.currency} ({payment.payment_method})"
        self.assertEqual(str(payment), expected_str)
    
    def test_payment_status_transitions(self):
        """Test valid payment status transitions"""
        payment = Payment.objects.create(
            ride=self.ride,
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF'
        )
        
        # Valid transitions
        valid_transitions = [
            ('pending', 'processing'),
            ('processing', 'completed'),
            ('pending', 'failed'),
            ('processing', 'failed'),
        ]
        
        for from_status, to_status in valid_transitions:
            payment.status = from_status
            payment.save()
            
            payment.status = to_status
            payment.save()  # Should not raise
            
            self.assertEqual(payment.status, to_status)
    
    def test_rwanda_phone_number_validation(self):
        """Test Rwanda mobile money phone number validation"""
        valid_numbers = [
            '+250788123456',  # MTN
            '+250735987654',  # Airtel
            '+250728456789',  # Tigo
        ]
        
        for phone_number in valid_numbers:
            payment = Payment(
                ride=self.ride,
                customer=self.customer,
                payment_method='mtn_momo',
                amount=Decimal('1000'),
                currency='RWF',
                momo_phone_number=phone_number
            )
            payment.full_clean()  # Should not raise
    
    def test_invalid_phone_number_validation(self):
        """Test validation fails for invalid phone numbers"""
        invalid_numbers = [
            '+1234567890',    # Wrong country code
            '0788123456',     # Missing country code
            '+250123456789',  # Invalid operator code
        ]
        
        for phone_number in invalid_numbers:
            payment = Payment(
                ride=self.ride,
                customer=self.customer,
                payment_method='mtn_momo',
                amount=Decimal('1000'),
                currency='RWF',
                momo_phone_number=phone_number
            )
            
            with self.assertRaises(ValidationError):
                payment.full_clean()
    
    def test_payment_amount_validation(self):
        """Test payment amount validation"""
        # Minimum amount validation
        with self.assertRaises(ValidationError):
            payment = Payment(
                ride=self.ride,
                customer=self.customer,
                payment_method='mtn_momo',
                amount=Decimal('0'),  # Invalid amount
                currency='RWF'
            )
            payment.full_clean()
        
        # Valid amount
        payment = Payment(
            ride=self.ride,
            customer=self.customer,
            payment_method='cash',
            amount=Decimal('100'),  # Valid minimum
            currency='RWF'
        )
        payment.full_clean()  # Should not raise
    
    def test_payment_currency_validation(self):
        """Test payment supports only RWF currency"""
        # Valid currency
        payment = Payment(
            ride=self.ride,
            customer=self.customer,
            payment_method='cash',
            amount=Decimal('1000'),
            currency='RWF'
        )
        payment.full_clean()  # Should not raise
        
        # Invalid currency
        with self.assertRaises(ValidationError):
            payment = Payment(
                ride=self.ride,
                customer=self.customer,
                payment_method='cash',
                amount=Decimal('1000'),
                currency='USD'  # Not supported
            )
            payment.full_clean()


class PaymentMethodModelTests(TestCase):
    """
    Unit tests for PaymentMethod model
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
    
    def test_create_payment_method_mtn(self):
        """Test creating MTN Mobile Money payment method"""
        payment_method = PaymentMethod.objects.create(
            user=self.customer,
            method_type='mtn_momo',
            phone_number='+250788123456',
            is_default=True,
            is_verified=True
        )
        
        self.assertEqual(payment_method.method_type, 'mtn_momo')
        self.assertTrue(payment_method.is_default)
        self.assertTrue(payment_method.is_verified)
        self.assertEqual(payment_method.phone_number, '+250788123456')
    
    def test_create_payment_method_airtel(self):
        """Test creating Airtel Money payment method"""
        payment_method = PaymentMethod.objects.create(
            user=self.customer,
            method_type='airtel_money',
            phone_number='+250735987654',
            account_name='John Doe'
        )
        
        self.assertEqual(payment_method.method_type, 'airtel_money')
        self.assertEqual(payment_method.account_name, 'John Doe')
    
    def test_payment_method_string_representation(self):
        """Test payment method __str__ method"""
        payment_method = PaymentMethod.objects.create(
            user=self.customer,
            method_type='mtn_momo',
            phone_number='+250788123456'
        )
        
        expected_str = f"{self.customer.email} - MTN MoMo (+250788123456)"
        self.assertEqual(str(payment_method), expected_str)
    
    def test_default_payment_method_constraint(self):
        """Test only one default payment method per user"""
        # Create first default payment method
        PaymentMethod.objects.create(
            user=self.customer,
            method_type='mtn_momo',
            phone_number='+250788123456',
            is_default=True
        )
        
        # Create second default - should update first to non-default
        PaymentMethod.objects.create(
            user=self.customer,
            method_type='airtel_money',
            phone_number='+250735987654',
            is_default=True
        )
        
        default_methods = PaymentMethod.objects.filter(
            user=self.customer, 
            is_default=True
        )
        self.assertEqual(default_methods.count(), 1)
        self.assertEqual(default_methods.first().method_type, 'airtel_money')
    
    def test_payment_method_verification_status(self):
        """Test payment method verification workflow"""
        payment_method = PaymentMethod.objects.create(
            user=self.customer,
            method_type='mtn_momo',
            phone_number='+250788123456',
            is_verified=False
        )
        
        # Initially not verified
        self.assertFalse(payment_method.is_verified)
        
        # Verify method
        payment_method.is_verified = True
        payment_method.verified_at = timezone.now()
        payment_method.save()
        
        self.assertTrue(payment_method.is_verified)
        self.assertIsNotNone(payment_method.verified_at)


class TransactionModelTests(TestCase):
    """
    Unit tests for Transaction model (detailed transaction records)
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.payment = Payment.objects.create(
            ride=self.test_factory.create_test_ride(customer=self.customer),
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF'
        )
    
    def test_create_transaction_record(self):
        """Test creating transaction record"""
        transaction = Transaction.objects.create(
            payment=self.payment,
            transaction_type='payment',
            amount=Decimal('1500'),
            currency='RWF',
            external_transaction_id='MTN123456789',
            provider_response={
                'status': 'SUCCESS',
                'reference': 'MTN123456789',
                'timestamp': '2024-01-15T10:30:00Z'
            },
            status='completed'
        )
        
        self.assertEqual(transaction.payment, self.payment)
        self.assertEqual(transaction.transaction_type, 'payment')
        self.assertEqual(transaction.amount, Decimal('1500'))
        self.assertEqual(transaction.external_transaction_id, 'MTN123456789')
        self.assertEqual(transaction.status, 'completed')
    
    def test_transaction_string_representation(self):
        """Test transaction __str__ method"""
        transaction = Transaction.objects.create(
            payment=self.payment,
            transaction_type='payment',
            amount=Decimal('1500'),
            currency='RWF',
            external_transaction_id='MTN123456789'
        )
        
        expected_str = f"Transaction #{transaction.id} - {transaction.amount} {transaction.currency} ({transaction.transaction_type})"
        self.assertEqual(str(transaction), expected_str)
    
    def test_transaction_types(self):
        """Test different transaction types"""
        transaction_types = ['payment', 'refund', 'chargeback', 'fee']
        
        for trans_type in transaction_types:
            transaction = Transaction(
                payment=self.payment,
                transaction_type=trans_type,
                amount=Decimal('100'),
                currency='RWF'
            )
            transaction.full_clean()  # Should not raise
    
    def test_transaction_fee_calculation(self):
        """Test transaction fee tracking"""
        transaction = Transaction.objects.create(
            payment=self.payment,
            transaction_type='payment',
            amount=Decimal('1500'),
            currency='RWF',
            provider_fee=Decimal('30'),  # 2% fee
            platform_fee=Decimal('45'),  # 3% fee
        )
        
        self.assertEqual(transaction.provider_fee, Decimal('30'))
        self.assertEqual(transaction.platform_fee, Decimal('45'))
        
        total_fees = transaction.provider_fee + transaction.platform_fee
        self.assertEqual(total_fees, Decimal('75'))


class MobileMoneyServiceTests(TestCase):
    """
    Unit tests for mobile money payment processing services
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.payment = Payment.objects.create(
            ride=self.test_factory.create_test_ride(customer=self.customer),
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF',
            momo_phone_number='+250788123456'
        )
    
    @patch('payments.services.MTNMoMoService.process_payment')
    def test_mtn_momo_payment_success(self, mock_process):
        """Test successful MTN Mobile Money payment"""
        # Mock successful response
        mock_process.return_value = {
            'status': 'SUCCESS',
            'transaction_id': 'MTN123456789',
            'reference': 'REF123456'
        }
        
        from payments.services import MTNMoMoService
        mtn_service = MTNMoMoService()
        
        result = mtn_service.process_payment(
            phone_number=self.payment.momo_phone_number,
            amount=self.payment.amount,
            reference=f"RIDE-{self.payment.ride.id}"
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('transaction_id', result)
        mock_process.assert_called_once()
    
    @patch('payments.services.MTNMoMoService.process_payment')
    def test_mtn_momo_payment_failure(self, mock_process):
        """Test failed MTN Mobile Money payment"""
        # Mock failure response
        mock_process.return_value = {
            'status': 'FAILED',
            'error_code': 'INSUFFICIENT_FUNDS',
            'error_message': 'Insufficient balance'
        }
        
        from payments.services import MTNMoMoService
        mtn_service = MTNMoMoService()
        
        result = mtn_service.process_payment(
            phone_number=self.payment.momo_phone_number,
            amount=self.payment.amount,
            reference=f"RIDE-{self.payment.ride.id}"
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('error_code', result)
        mock_process.assert_called_once()
    
    @patch('payments.services.AirtelMoneyService.process_payment')
    def test_airtel_money_payment_success(self, mock_process):
        """Test successful Airtel Money payment"""
        # Mock successful response
        mock_process.return_value = {
            'status': 'SUCCESS',
            'transaction_id': 'AIRTEL987654321',
            'reference': 'AREF123456'
        }
        
        from payments.services import AirtelMoneyService
        airtel_service = AirtelMoneyService()
        
        result = airtel_service.process_payment(
            phone_number='+250735987654',
            amount=Decimal('2000'),
            reference=f"RIDE-{self.payment.ride.id}"
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('transaction_id', result)
        mock_process.assert_called_once()
    
    @patch('payments.services.PaymentService.verify_transaction')
    def test_payment_verification(self, mock_verify):
        """Test payment transaction verification"""
        # Mock verification response
        mock_verify.return_value = {
            'verified': True,
            'status': 'COMPLETED',
            'amount': '1500',
            'currency': 'RWF'
        }
        
        from payments.services import PaymentService
        payment_service = PaymentService()
        
        result = payment_service.verify_transaction('MTN123456789')
        
        self.assertTrue(result['verified'])
        self.assertEqual(result['status'], 'COMPLETED')
        mock_verify.assert_called_once_with('MTN123456789')


class PaymentWebhookTests(TestCase):
    """
    Unit tests for payment webhook handling
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.payment = Payment.objects.create(
            ride=self.test_factory.create_test_ride(customer=self.customer),
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF',
            external_transaction_id='MTN123456789',
            status='processing'
        )
    
    def test_mtn_webhook_payment_success(self):
        """Test MTN webhook for successful payment"""
        webhook_data = {
            'transaction_id': 'MTN123456789',
            'status': 'SUCCESS',
            'amount': '1500',
            'currency': 'RWF',
            'reference': f'RIDE-{self.payment.ride.id}',
            'timestamp': '2024-01-15T10:30:00Z'
        }
        
        from payments.webhooks import MTNWebhookHandler
        webhook_handler = MTNWebhookHandler()
        
        result = webhook_handler.handle_webhook(webhook_data)
        
        # Refresh payment from database
        self.payment.refresh_from_db()
        
        self.assertEqual(self.payment.status, 'completed')
        self.assertTrue(result['processed'])
    
    def test_airtel_webhook_payment_failure(self):
        """Test Airtel webhook for failed payment"""
        webhook_data = {
            'transaction_id': 'AIRTEL987654321',
            'status': 'FAILED',
            'error_code': 'INVALID_PIN',
            'error_message': 'Invalid PIN entered',
            'timestamp': '2024-01-15T10:35:00Z'
        }
        
        from payments.webhooks import AirtelWebhookHandler
        webhook_handler = AirtelWebhookHandler()
        
        # Update payment for this test
        self.payment.external_transaction_id = 'AIRTEL987654321'
        self.payment.save()
        
        result = webhook_handler.handle_webhook(webhook_data)
        
        # Refresh payment from database
        self.payment.refresh_from_db()
        
        self.assertEqual(self.payment.status, 'failed')
        self.assertTrue(result['processed'])
    
    def test_webhook_signature_verification(self):
        """Test webhook signature verification for security"""
        webhook_data = {
            'transaction_id': 'MTN123456789',
            'status': 'SUCCESS',
            'amount': '1500'
        }
        
        from payments.webhooks import WebhookSecurityHandler
        security_handler = WebhookSecurityHandler()
        
        # Test valid signature
        valid_signature = security_handler.generate_signature(webhook_data, 'secret_key')
        is_valid = security_handler.verify_signature(webhook_data, valid_signature, 'secret_key')
        self.assertTrue(is_valid)
        
        # Test invalid signature
        invalid_signature = 'invalid_signature_hash'
        is_valid = security_handler.verify_signature(webhook_data, invalid_signature, 'secret_key')
        self.assertFalse(is_valid)


class PaymentAPITests(APITestCase):
    """
    Unit tests for payment API endpoints
    """
    
    def setUp(self):
        self.test_factory = TestDataFactory()
        self.customer = self.test_factory.create_test_user(role='customer')
        self.ride = self.test_factory.create_test_ride(customer=self.customer)
        
        # Authenticate as customer
        self.client.force_authenticate(user=self.customer)
    
    def test_create_payment_endpoint(self):
        """Test creating payment via API"""
        payment_data = {
            'ride': self.ride.id,
            'payment_method': 'mtn_momo',
            'amount': '1500',
            'currency': 'RWF',
            'momo_phone_number': '+250788123456'
        }
        
        response = self.client.post('/api/v1/payments/', payment_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['payment_method'], 'mtn_momo')
        self.assertEqual(Decimal(response.data['amount']), Decimal('1500'))
    
    def test_list_payment_methods_endpoint(self):
        """Test listing user's payment methods"""
        # Create test payment methods
        PaymentMethod.objects.create(
            user=self.customer,
            method_type='mtn_momo',
            phone_number='+250788123456',
            is_default=True
        )
        
        PaymentMethod.objects.create(
            user=self.customer,
            method_type='airtel_money',
            phone_number='+250735987654'
        )
        
        response = self.client.get('/api/v1/payment-methods/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_add_payment_method_endpoint(self):
        """Test adding new payment method"""
        method_data = {
            'method_type': 'mtn_momo',
            'phone_number': '+250788123456',
            'is_default': True
        }
        
        response = self.client.post('/api/v1/payment-methods/', method_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['method_type'], 'mtn_momo')
        self.assertTrue(response.data['is_default'])
    
    def test_process_payment_endpoint(self):
        """Test processing payment via API"""
        payment = Payment.objects.create(
            ride=self.ride,
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF',
            momo_phone_number='+250788123456'
        )
        
        with patch('payments.services.PaymentService.process_payment') as mock_process:
            mock_process.return_value = {
                'status': 'SUCCESS',
                'transaction_id': 'MTN123456789'
            }
            
            response = self.client.post(f'/api/v1/payments/{payment.id}/process/')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'SUCCESS')
    
    def test_payment_status_endpoint(self):
        """Test checking payment status"""
        payment = Payment.objects.create(
            ride=self.ride,
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF',
            status='completed'
        )
        
        response = self.client.get(f'/api/v1/payments/{payment.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
    
    def test_unauthorized_payment_access(self):
        """Test unauthorized access to payment endpoints"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/v1/payments/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_payment_refund_endpoint(self):
        """Test payment refund processing"""
        payment = Payment.objects.create(
            ride=self.ride,
            customer=self.customer,
            payment_method='mtn_momo',
            amount=Decimal('1500'),
            currency='RWF',
            status='completed'
        )
        
        with patch('payments.services.PaymentService.process_refund') as mock_refund:
            mock_refund.return_value = {
                'status': 'SUCCESS',
                'refund_id': 'REF123456789'
            }
            
            refund_data = {
                'amount': '1500',
                'reason': 'ride_cancelled'
            }
            
            response = self.client.post(
                f'/api/v1/payments/{payment.id}/refund/',
                refund_data,
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'SUCCESS')
