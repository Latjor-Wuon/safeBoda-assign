"""
Async Payment Processing Service for SafeBoda Rwanda
Complete asynchronous payment workflow with error handling and resilience
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from celery import shared_task, current_app
from channels.layers import get_channel_layer

from .models import Transaction, PaymentMethod
from .services import MTNMoMoService, AirtelMoneyService
from bookings.models import Ride
from notifications.services import NotificationService
from analytics.services import AnalyticsService

logger = logging.getLogger(__name__)
User = get_user_model()


class PaymentStatus(Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentError(Exception):
    """Base payment error class"""
    pass


class NetworkError(PaymentError):
    """Network connectivity error"""
    pass


class InsufficientFundsError(PaymentError):
    """Insufficient funds error"""
    pass


class InvalidAccountError(PaymentError):
    """Invalid account error"""
    pass


class ProviderDowntimeError(PaymentError):
    """Payment provider downtime error"""
    pass


@dataclass
class PaymentResult:
    """Payment processing result"""
    success: bool
    transaction_id: Optional[str] = None
    provider_reference: Optional[str] = None
    status: str = PaymentStatus.PENDING.value
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_recommended: bool = False
    estimated_completion: Optional[datetime] = None


@dataclass
class PaymentContext:
    """Payment processing context"""
    transaction: Transaction
    ride: Optional[Ride] = None
    payment_method: Optional[PaymentMethod] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None


class AsyncPaymentProcessor:
    """
    Asynchronous payment processing service with comprehensive error handling
    """
    
    def __init__(self):
        self.mtn_service = MTNMoMoService()
        self.airtel_service = AirtelMoneyService()
        self.notification_service = NotificationService()
        self.analytics_service = AnalyticsService()
        self.channel_layer = get_channel_layer()
        
        # Configuration
        self.MAX_RETRIES = 3
        self.RETRY_BASE_DELAY = 30  # seconds
        self.PAYMENT_TIMEOUT = 300  # 5 minutes
        
        # Cache keys
        self.PAYMENT_CACHE_KEY = "payment_status_{transaction_id}"
        self.PROVIDER_STATUS_KEY = "provider_status_{provider}"
        self.USER_PAYMENT_LIMIT_KEY = "payment_limit_{user_id}"
    
    async def process_payment_async(self, payment_data: Dict[str, Any], user: User) -> PaymentResult:
        """
        Main async payment processing entry point
        """
        try:
            # Step 1: Validate payment request
            validation_result = await self._validate_payment_request(payment_data, user)
            if not validation_result.success:
                return validation_result
            
            # Step 2: Create transaction record
            with transaction.atomic():
                transaction_obj = await self._create_transaction(payment_data, user)
                
                # Step 3: Create payment context
                context = PaymentContext(
                    transaction=transaction_obj,
                    ride=await self._get_ride(payment_data.get('ride_id')),
                    metadata=payment_data.get('metadata', {})
                )
                
                # Step 4: Cache initial status
                await self._cache_payment_status(transaction_obj)
                
                # Step 5: Start async processing
                task_id = await self._schedule_payment_processing(context)
                
                # Step 6: Send initial notifications
                await self._send_payment_notification(context, 'initiated')
                
                # Step 7: Record analytics
                await self._record_payment_analytics(context, 'initiated')
                
                return PaymentResult(
                    success=True,
                    transaction_id=str(transaction_obj.id),
                    status=PaymentStatus.PROCESSING.value,
                    estimated_completion=timezone.now() + timedelta(seconds=self.PAYMENT_TIMEOUT)
                )
                
        except Exception as e:
            logger.error(f"Payment processing failed: {str(e)}", exc_info=True)
            return PaymentResult(
                success=False,
                error_message="Payment processing failed",
                error_code="PROCESSING_ERROR"
            )
    
    async def _validate_payment_request(self, payment_data: Dict[str, Any], user: User) -> PaymentResult:
        """Validate payment request with comprehensive checks"""
        
        # 1. Required field validation
        required_fields = ['amount', 'payment_method']
        for field in required_fields:
            if field not in payment_data:
                return PaymentResult(
                    success=False,
                    error_message=f"Missing required field: {field}",
                    error_code="MISSING_FIELD"
                )
        
        # 2. Amount validation
        amount = Decimal(str(payment_data['amount']))
        if amount <= 0:
            return PaymentResult(
                success=False,
                error_message="Amount must be greater than zero",
                error_code="INVALID_AMOUNT"
            )
        
        if amount > Decimal('100000'):  # 100k RWF limit
            return PaymentResult(
                success=False,
                error_message="Amount exceeds maximum limit",
                error_code="AMOUNT_LIMIT_EXCEEDED"
            )
        
        # 3. Rate limiting check
        if not await self._check_rate_limit(user):
            return PaymentResult(
                success=False,
                error_message="Payment rate limit exceeded",
                error_code="RATE_LIMIT_EXCEEDED"
            )
        
        # 4. Provider availability check
        provider = payment_data['payment_method']
        if not await self._check_provider_availability(provider):
            return PaymentResult(
                success=False,
                error_message=f"Payment provider {provider} is currently unavailable",
                error_code="PROVIDER_UNAVAILABLE"
            )
        
        # 5. Account verification (for mobile money)
        if provider in ['mtn_momo', 'airtel_money']:
            phone_number = payment_data.get('phone_number')
            if not phone_number:
                return PaymentResult(
                    success=False,
                    error_message="Phone number required for mobile money payments",
                    error_code="MISSING_PHONE_NUMBER"
                )
            
            if not await self._validate_phone_number(phone_number, provider):
                return PaymentResult(
                    success=False,
                    error_message="Invalid phone number for selected provider",
                    error_code="INVALID_PHONE_NUMBER"
                )
        
        return PaymentResult(success=True)
    
    async def _create_transaction(self, payment_data: Dict[str, Any], user: User) -> Transaction:
        """Create transaction record"""
        
        ride = None
        if payment_data.get('ride_id'):
            ride = await Ride.objects.aget(id=payment_data['ride_id'])
        
        transaction_obj = await Transaction.objects.acreate(
            transaction_type='ride_payment' if ride else 'topup',
            from_user=user,
            to_user=ride.driver if ride else None,
            amount=Decimal(str(payment_data['amount'])),
            provider=payment_data['payment_method'],
            description=payment_data.get('description', 'SafeBoda payment'),
            ride=ride,
            metadata=payment_data.get('metadata', {})
        )
        
        return transaction_obj
    
    async def _schedule_payment_processing(self, context: PaymentContext) -> str:
        """Schedule async payment processing"""
        task_id = str(uuid.uuid4())
        
        # Schedule Celery task
        current_app.send_task(
            'payments.process_payment_task',
            args=[str(context.transaction.id)],
            task_id=task_id,
            countdown=1  # Start processing after 1 second
        )
        
        return task_id
    
    async def process_provider_payment(self, context: PaymentContext) -> PaymentResult:
        """Process payment with specific provider"""
        
        provider = context.transaction.provider
        
        try:
            if provider == 'mtn_momo':
                result = await self._process_mtn_payment(context)
            elif provider == 'airtel_money':
                result = await self._process_airtel_payment(context)
            elif provider == 'cash':
                result = await self._process_cash_payment(context)
            else:
                raise PaymentError(f"Unsupported payment provider: {provider}")
            
            # Update transaction status
            await self._update_transaction_status(context.transaction, result)
            
            # Cache updated status
            await self._cache_payment_status(context.transaction)
            
            # Send real-time update
            await self._broadcast_payment_update(context, result)
            
            # Send notification
            await self._send_payment_notification(context, result.status)
            
            # Record analytics
            await self._record_payment_analytics(context, result.status)
            
            return result
            
        except NetworkError as e:
            logger.warning(f"Network error for transaction {context.transaction.id}: {str(e)}")
            return await self._handle_network_error(context, e)
            
        except InsufficientFundsError as e:
            logger.info(f"Insufficient funds for transaction {context.transaction.id}: {str(e)}")
            return await self._handle_insufficient_funds(context, e)
            
        except InvalidAccountError as e:
            logger.warning(f"Invalid account for transaction {context.transaction.id}: {str(e)}")
            return await self._handle_invalid_account(context, e)
            
        except ProviderDowntimeError as e:
            logger.error(f"Provider downtime for transaction {context.transaction.id}: {str(e)}")
            return await self._handle_provider_downtime(context, e)
            
        except Exception as e:
            logger.error(f"Unexpected payment error for transaction {context.transaction.id}: {str(e)}", exc_info=True)
            return await self._handle_unexpected_error(context, e)
    
    async def _process_mtn_payment(self, context: PaymentContext) -> PaymentResult:
        """Process MTN Mobile Money payment"""
        
        transaction = context.transaction
        phone_number = transaction.metadata.get('phone_number')
        
        if not phone_number:
            raise InvalidAccountError("Phone number not provided")
        
        try:
            # Request payment from MTN API
            result = await self.mtn_service.request_payment(
                phone_number=phone_number,
                amount=transaction.amount,
                external_id=str(transaction.id),
                payer_message="SafeBoda ride payment",
                payee_note=f"Payment for transaction {transaction.id}"
            )
            
            if result.success:
                # Store provider reference
                transaction.provider_transaction_id = result.transaction_id
                await transaction.asave()
                
                # Schedule status check
                await self._schedule_status_check(transaction, delay=30)
                
                return PaymentResult(
                    success=True,
                    transaction_id=str(transaction.id),
                    provider_reference=result.transaction_id,
                    status=PaymentStatus.PROCESSING.value,
                    estimated_completion=timezone.now() + timedelta(minutes=2)
                )
            else:
                raise PaymentError(f"MTN payment failed: {result.error_message}")
                
        except Exception as e:
            # Classify error type
            if "network" in str(e).lower() or "timeout" in str(e).lower():
                raise NetworkError(str(e))
            elif "insufficient" in str(e).lower():
                raise InsufficientFundsError(str(e))
            elif "invalid" in str(e).lower():
                raise InvalidAccountError(str(e))
            else:
                raise PaymentError(str(e))
    
    async def _process_airtel_payment(self, context: PaymentContext) -> PaymentResult:
        """Process Airtel Money payment"""
        
        transaction = context.transaction
        phone_number = transaction.metadata.get('phone_number')
        
        if not phone_number:
            raise InvalidAccountError("Phone number not provided")
        
        try:
            result = await self.airtel_service.request_payment(
                phone_number=phone_number,
                amount=transaction.amount,
                transaction_id=str(transaction.id),
                reference=f"SAFEBODA-{transaction.id}"
            )
            
            if result.success:
                transaction.provider_transaction_id = result.transaction_id
                await transaction.asave()
                
                await self._schedule_status_check(transaction, delay=30)
                
                return PaymentResult(
                    success=True,
                    transaction_id=str(transaction.id),
                    provider_reference=result.transaction_id,
                    status=PaymentStatus.PROCESSING.value,
                    estimated_completion=timezone.now() + timedelta(minutes=2)
                )
            else:
                raise PaymentError(f"Airtel payment failed: {result.error_message}")
                
        except Exception as e:
            if "network" in str(e).lower():
                raise NetworkError(str(e))
            elif "insufficient" in str(e).lower():
                raise InsufficientFundsError(str(e))
            else:
                raise PaymentError(str(e))
    
    async def _process_cash_payment(self, context: PaymentContext) -> PaymentResult:
        """Process cash payment"""
        
        transaction = context.transaction
        
        # Cash payments are marked as completed immediately
        # Driver will collect cash and platform will deduct commission
        
        return PaymentResult(
            success=True,
            transaction_id=str(transaction.id),
            status=PaymentStatus.COMPLETED.value,
            estimated_completion=timezone.now()
        )
    
    # Error Handling Methods
    
    async def _handle_network_error(self, context: PaymentContext, error: NetworkError) -> PaymentResult:
        """Handle network errors with retry logic"""
        
        context.retry_count += 1
        
        if context.retry_count <= self.MAX_RETRIES:
            # Schedule retry with exponential backoff
            delay = self.RETRY_BASE_DELAY * (2 ** (context.retry_count - 1))
            
            await self._schedule_payment_retry(context, delay)
            
            return PaymentResult(
                success=False,
                error_message="Network error - payment will be retried",
                error_code="NETWORK_ERROR",
                retry_recommended=True
            )
        else:
            # Max retries exceeded
            return PaymentResult(
                success=False,
                error_message="Payment failed after maximum retries",
                error_code="MAX_RETRIES_EXCEEDED"
            )
    
    async def _handle_insufficient_funds(self, context: PaymentContext, error: InsufficientFundsError) -> PaymentResult:
        """Handle insufficient funds error"""
        
        # Notify customer about insufficient funds
        await self._send_payment_notification(context, 'insufficient_funds')
        
        # Suggest alternative payment methods
        await self._suggest_alternative_payment(context)
        
        return PaymentResult(
            success=False,
            error_message="Insufficient funds in your account",
            error_code="INSUFFICIENT_FUNDS"
        )
    
    async def _handle_invalid_account(self, context: PaymentContext, error: InvalidAccountError) -> PaymentResult:
        """Handle invalid account error"""
        
        await self._send_payment_notification(context, 'invalid_account')
        
        return PaymentResult(
            success=False,
            error_message="Invalid payment account. Please check your phone number.",
            error_code="INVALID_ACCOUNT"
        )
    
    async def _handle_provider_downtime(self, context: PaymentContext, error: ProviderDowntimeError) -> PaymentResult:
        """Handle provider downtime"""
        
        # Try alternative provider if available
        alternative_result = await self._try_alternative_provider(context)
        
        if alternative_result.success:
            return alternative_result
        
        # Schedule retry for later
        await self._schedule_payment_retry(context, delay=300)  # 5 minutes
        
        return PaymentResult(
            success=False,
            error_message="Payment provider is temporarily unavailable",
            error_code="PROVIDER_DOWNTIME",
            retry_recommended=True
        )
    
    async def _handle_unexpected_error(self, context: PaymentContext, error: Exception) -> PaymentResult:
        """Handle unexpected errors"""
        
        # Log detailed error information
        logger.error(f"Unexpected payment error: {str(error)}", exc_info=True)
        
        # Notify admin team
        await self._notify_admin_team(context, error)
        
        return PaymentResult(
            success=False,
            error_message="Payment processing failed due to system error",
            error_code="SYSTEM_ERROR"
        )
    
    # Helper Methods
    
    async def _cache_payment_status(self, transaction: Transaction):
        """Cache payment status for quick retrieval"""
        cache_key = self.PAYMENT_CACHE_KEY.format(transaction_id=transaction.id)
        status_data = {
            'status': transaction.status,
            'amount': float(transaction.amount),
            'provider': transaction.provider,
            'created_at': transaction.created_at.isoformat(),
            'updated_at': transaction.updated_at.isoformat()
        }
        cache.set(cache_key, status_data, 3600)  # Cache for 1 hour
    
    async def _broadcast_payment_update(self, context: PaymentContext, result: PaymentResult):
        """Broadcast payment update via WebSocket"""
        if self.channel_layer:
            await self.channel_layer.group_send(
                f"payment_{context.transaction.id}",
                {
                    'type': 'payment_status_update',
                    'transaction_id': str(context.transaction.id),
                    'status': result.status,
                    'success': result.success,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    async def _send_payment_notification(self, context: PaymentContext, event_type: str):
        """Send payment-related notifications"""
        await self.notification_service.send_payment_notification(
            transaction=context.transaction,
            event_type=event_type,
            user=context.transaction.from_user
        )
    
    async def _record_payment_analytics(self, context: PaymentContext, event_type: str):
        """Record payment analytics"""
        await self.analytics_service.record_payment_event(
            transaction=context.transaction,
            event_type=event_type,
            metadata=context.metadata
        )
    
    async def _schedule_payment_retry(self, context: PaymentContext, delay: int):
        """Schedule payment retry"""
        current_app.send_task(
            'payments.retry_payment_task',
            args=[str(context.transaction.id), context.retry_count],
            countdown=delay
        )
    
    async def _schedule_status_check(self, transaction: Transaction, delay: int):
        """Schedule payment status check"""
        current_app.send_task(
            'payments.check_payment_status_task',
            args=[str(transaction.id)],
            countdown=delay
        )
    
    async def _check_rate_limit(self, user: User) -> bool:
        """Check payment rate limit for user"""
        cache_key = self.USER_PAYMENT_LIMIT_KEY.format(user_id=user.id)
        payment_count = cache.get(cache_key, 0)
        
        if payment_count >= 10:  # Max 10 payments per hour
            return False
        
        cache.set(cache_key, payment_count + 1, 3600)  # 1 hour window
        return True
    
    async def _check_provider_availability(self, provider: str) -> bool:
        """Check if payment provider is available"""
        cache_key = self.PROVIDER_STATUS_KEY.format(provider=provider)
        status = cache.get(cache_key)
        
        if status:
            return status.get('available', True)
        
        # Default to available if no cached status
        return True
    
    async def _validate_phone_number(self, phone_number: str, provider: str) -> bool:
        """Validate phone number for provider"""
        if provider == 'mtn_momo':
            # MTN Rwanda numbers start with +25078
            return phone_number.startswith('+25078')
        elif provider == 'airtel_money':
            # Airtel Rwanda numbers start with +25073
            return phone_number.startswith('+25073')
        
        return False
    
    async def _get_ride(self, ride_id: Optional[str]) -> Optional[Ride]:
        """Get ride object if ride_id provided"""
        if ride_id:
            try:
                return await Ride.objects.aget(id=ride_id)
            except Ride.DoesNotExist:
                return None
        return None
    
    async def _update_transaction_status(self, transaction: Transaction, result: PaymentResult):
        """Update transaction status based on result"""
        transaction.status = result.status
        if result.provider_reference:
            transaction.provider_transaction_id = result.provider_reference
        if not result.success:
            transaction.failure_reason = result.error_message
        await transaction.asave()
    
    async def _try_alternative_provider(self, context: PaymentContext) -> PaymentResult:
        """Try alternative payment provider"""
        # Implementation for provider failover
        # This would attempt to use a different provider if available
        return PaymentResult(success=False, error_message="No alternative provider available")
    
    async def _suggest_alternative_payment(self, context: PaymentContext):
        """Suggest alternative payment methods to user"""
        # Send notification with alternative payment options
        pass
    
    async def _notify_admin_team(self, context: PaymentContext, error: Exception):
        """Notify admin team about payment errors"""
        # Send alert to admin team about system errors
        pass


# Celery Tasks
@shared_task(bind=True, max_retries=3)
def process_payment_task(self, transaction_id: str):
    """Celery task for async payment processing"""
    try:
        processor = AsyncPaymentProcessor()
        transaction = Transaction.objects.get(id=transaction_id)
        
        context = PaymentContext(transaction=transaction)
        
        # Use asyncio to run async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                processor.process_provider_payment(context)
            )
            
            if not result.success and result.retry_recommended:
                raise PaymentError(result.error_message)
                
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Payment task failed for transaction {transaction_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def retry_payment_task(transaction_id: str, retry_count: int):
    """Celery task for payment retry"""
    try:
        processor = AsyncPaymentProcessor()
        transaction = Transaction.objects.get(id=transaction_id)
        
        context = PaymentContext(
            transaction=transaction,
            retry_count=retry_count
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                processor.process_provider_payment(context)
            )
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Payment retry failed for transaction {transaction_id}: {str(e)}")


@shared_task
def check_payment_status_task(transaction_id: str):
    """Celery task for checking payment status"""
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        
        if transaction.provider == 'mtn_momo':
            service = MTNMoMoService()
            status_result = service.check_payment_status(transaction.provider_transaction_id)
        elif transaction.provider == 'airtel_money':
            service = AirtelMoneyService()
            status_result = service.check_payment_status(transaction.provider_transaction_id)
        else:
            return  # No status check needed for cash payments
        
        # Update transaction based on status
        if status_result.status == 'SUCCESSFUL':
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
        elif status_result.status == 'FAILED':
            transaction.status = 'failed'
            transaction.failure_reason = status_result.reason
        
        transaction.save()
        
        # Send notification about status update
        notification_service = NotificationService()
        notification_service.send_payment_status_update(transaction)
        
    except Exception as e:
        logger.error(f"Status check failed for transaction {transaction_id}: {str(e)}")