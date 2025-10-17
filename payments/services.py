"""
Payment processing services for SafeBoda Rwanda
Handles mobile money integration with MTN, Airtel, etc.
"""
import requests
import uuid
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import PaymentMethod, Transaction
from bookings.models import Ride
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class PaymentProcessingService:
    """Main service for payment processing"""
    
    def __init__(self):
        self.mtn_service = MTNMoMoService()
        self.airtel_service = AirtelMoneyService()
    
    def process_payment(self, user, amount, provider, phone_number=None, description="", ride_id=None):
        """
        Process payment using specified provider
        """
        try:
            # Create transaction record
            transaction = Transaction.objects.create(
                from_user=user,
                transaction_type='ride_payment',
                amount=amount,
                currency='RWF',
                provider=provider,
                description=description,
                ride_id=ride_id
            )
            
            # Process based on provider
            if provider == 'mtn_momo':
                result = self.mtn_service.process_payment(transaction, phone_number)
            elif provider == 'airtel_money':
                result = self.airtel_service.process_payment(transaction, phone_number)
            else:
                result = {'success': False, 'error': 'Unsupported payment provider'}
            
            # Update transaction status
            if result['success']:
                transaction.status = 'processing'
                transaction.provider_transaction_id = result.get('transaction_id')
                transaction.save()
            else:
                transaction.status = 'failed'
                transaction.save()
            
            return {
                'success': result['success'],
                'transaction_id': transaction.id,
                'provider_transaction_id': result.get('transaction_id'),
                'status': transaction.status,
                'message': result.get('message', 'Payment processed'),
                'amount': transaction.amount
            }
            
        except Exception as e:
            logger.error(f"Payment processing error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Payment processing failed'
            }
    
    def check_payment_status(self, transaction):
        """Check payment status with provider"""
        try:
            if transaction.provider == 'mtn_momo':
                return self.mtn_service.check_status(transaction)
            elif transaction.provider == 'airtel_money':
                return self.airtel_service.check_status(transaction)
            else:
                return transaction.status
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return transaction.status


class MTNMoMoService:
    """MTN Mobile Money service for Rwanda"""
    
    def __init__(self):
        self.api_url = getattr(settings, 'MTN_MOMO_API_URL', 'https://sandbox.momodeveloper.mtn.com')
        self.api_key = getattr(settings, 'MTN_MOMO_API_KEY', '')
        self.subscription_key = getattr(settings, 'MTN_MOMO_SUBSCRIPTION_KEY', '')
    
    def process_payment(self, transaction, phone_number):
        """Process MTN MoMo payment"""
        try:
            # Prepare payment request
            payment_data = {
                'amount': str(transaction.amount),
                'currency': 'RWF',
                'externalId': str(transaction.id),
                'payer': {
                    'partyIdType': 'MSISDN',
                    'partyId': phone_number or transaction.from_user.phone_number
                },
                'payerMessage': transaction.description,
                'payeeNote': f'SafeBoda payment for {transaction.description}'
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'X-Reference-Id': str(uuid.uuid4()),
                'X-Target-Environment': 'sandbox',
                'Ocp-Apim-Subscription-Key': self.subscription_key,
                'Content-Type': 'application/json'
            }
            
            # In production, this would make an actual API call
            # response = requests.post(f'{self.api_url}/collection/v1_0/requesttopay', 
            #                         json=payment_data, headers=headers)
            
            # Simulate successful response for development
            return {
                'success': True,
                'transaction_id': f'MTN{str(uuid.uuid4())[:8]}',
                'message': 'MTN MoMo payment initiated successfully'
            }
            
        except Exception as e:
            logger.error(f"MTN MoMo payment error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_status(self, transaction):
        """Check MTN MoMo payment status"""
        try:
            # Simulate status check - in production would call MTN API
            import random
            if random.random() > 0.2:  # 80% success rate
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
            else:
                transaction.status = 'failed'
            
            transaction.save()
            return transaction.status
            
        except Exception as e:
            logger.error(f"MTN status check error: {str(e)}")
            return transaction.status


class AirtelMoneyService:
    """Airtel Money service for Rwanda"""
    
    def __init__(self):
        self.api_url = getattr(settings, 'AIRTEL_MONEY_API_URL', 'https://openapiuat.airtel.africa')
        self.client_id = getattr(settings, 'AIRTEL_MONEY_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'AIRTEL_MONEY_CLIENT_SECRET', '')
    
    def process_payment(self, transaction, phone_number):
        """Process Airtel Money payment"""
        try:
            # Prepare payment request
            payment_data = {
                'reference': str(transaction.id),
                'subscriber': {
                    'country': 'RW',
                    'currency': 'RWF',
                    'msisdn': phone_number or transaction.from_user.phone_number
                },
                'transaction': {
                    'amount': str(transaction.amount),
                    'country': 'RW',
                    'currency': 'RWF',
                    'id': str(transaction.id)
                }
            }
            
            # In production, this would make an actual API call
            # headers = {'Authorization': f'Bearer {self.get_access_token()}'}
            # response = requests.post(f'{self.api_url}/merchant/v1/payments/', 
            #                         json=payment_data, headers=headers)
            
            # Simulate successful response for development
            return {
                'success': True,
                'transaction_id': f'AIRTEL{str(uuid.uuid4())[:8]}',
                'message': 'Airtel Money payment initiated successfully'
            }
            
        except Exception as e:
            logger.error(f"Airtel Money payment error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_status(self, transaction):
        """Check Airtel Money payment status"""
        try:
            # Simulate status check - in production would call Airtel API
            import random
            if random.random() > 0.25:  # 75% success rate
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
            else:
                transaction.status = 'failed'
            
            transaction.save()
            return transaction.status
            
        except Exception as e:
            logger.error(f"Airtel status check error: {str(e)}")
            return transaction.status


class MobileMoneyService:
    """Generic mobile money service wrapper"""
    
    @staticmethod
    def get_provider_service(provider):
        """Get appropriate service for provider"""
        if provider == 'mtn_momo':
            return MTNMoMoService()
        elif provider == 'airtel_money':
            return AirtelMoneyService()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @staticmethod
    def validate_phone_number(phone_number, provider):
        """Validate phone number for specific provider"""
        if not phone_number.startswith('+250'):
            return False
        
        # MTN numbers start with +25078
        if provider == 'mtn_momo':
            return phone_number.startswith('+25078')
        
        # Airtel numbers start with +25073
        elif provider == 'airtel_money':
            return phone_number.startswith('+25073')
        
        return True
    
    @staticmethod
    def calculate_fees(amount, provider):
        """Calculate transaction fees"""
        if provider == 'mtn_momo':
            if amount <= 1000:
                return Decimal('50')
            elif amount <= 5000:
                return Decimal('100')
            else:
                return amount * Decimal('0.02')  # 2%
        
        elif provider == 'airtel_money':
            if amount <= 1000:
                return Decimal('40')
            elif amount <= 5000:
                return Decimal('90')
            else:
                return amount * Decimal('0.018')  # 1.8%
        
        return Decimal('0')