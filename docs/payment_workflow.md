# Payment Workflow Documentation - SafeBoda Rwanda

## Overview
Complete payment system design for SafeBoda Rwanda platform with integrated mobile money support, focusing on MTN Mobile Money and Airtel Money - the two dominant payment providers in Rwanda.

## System Architecture

### Payment Service Integration
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Customer App  │    │   Driver App    │    │  Admin Panel    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ HTTP/REST API        │                      │
          │                      │                      │
┌─────────▼──────────────────────▼──────────────────────▼───────┐
│                SafeBoda Payment Gateway                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │ Payment Service │  │ Async Processor │  │ Webhook Handler ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└───────────┬─────────────────────┬─────────────────────────────┘
            │                     │
   ┌────────▼─────────┐  ┌─────────▼─────────┐
   │  MTN MoMo API    │  │  Airtel Money API │
   │  Collections     │  │  Disbursements    │
   └──────────────────┘  └───────────────────┘
```

## Payment Methods

### 1. MTN Mobile Money (MoMo)
- **Primary Provider**: Most widely used in Rwanda (>70% market share)
- **API Integration**: MTN OpenAPI Platform
- **Transaction Types**: Collections, Disbursements, Account Balance
- **Security**: OAuth 2.0, API Keys, Request Signing

### 2. Airtel Money
- **Secondary Provider**: Second largest mobile money provider
- **API Integration**: Airtel Money API
- **Transaction Types**: Merchant Payments, Money Transfer
- **Security**: JWT Tokens, API Authentication

### 3. Cash Payments
- **Fallback Method**: Available for all rides
- **Processing**: Driver collects, platform commission deducted
- **Settlement**: Weekly driver payouts

## Payment Workflow Design

### 1. Ride Payment Flow

#### A. Customer Payment (Collections)
```python
# 1. Ride Completion Trigger
async def process_ride_payment(ride_id: str):
    ride = await get_ride(ride_id)
    
    # 2. Determine Payment Method
    if ride.payment_method == 'mtn_momo':
        result = await process_mtn_payment(ride)
    elif ride.payment_method == 'airtel_money':
        result = await process_airtel_payment(ride)
    elif ride.payment_method == 'cash':
        result = await process_cash_payment(ride)
    
    # 3. Update Transaction Status
    await update_payment_status(ride, result)
    
    # 4. Trigger Driver Payout (if successful)
    if result.success:
        await schedule_driver_payout(ride)
```

#### B. MTN Mobile Money Integration
```python
class MTNMoMoService:
    """MTN Mobile Money Collections API Integration"""
    
    async def request_payment(self, phone_number: str, amount: Decimal, 
                            external_id: str) -> PaymentResult:
        """
        Initiate payment request to customer
        """
        # 1. Generate Access Token
        token = await self.get_access_token()
        
        # 2. Create Payment Request
        payment_data = {
            "amount": str(amount),
            "currency": "RWF",
            "externalId": external_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_number
            },
            "payerMessage": "SafeBoda ride payment",
            "payeeNote": f"Payment for ride {external_id}"
        }
        
        # 3. Send Request to MTN API
        response = await self.make_api_request(
            method="POST",
            endpoint="/collection/v1_0/requesttopay",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Reference-Id": str(uuid.uuid4()),
                "X-Target-Environment": "mtnrwanda",
                "Ocp-Apim-Subscription-Key": self.subscription_key
            },
            data=payment_data
        )
        
        # 4. Return Result
        return PaymentResult(
            success=response.status_code == 202,
            transaction_id=response.headers.get("X-Reference-Id"),
            status="pending"
        )
    
    async def check_payment_status(self, reference_id: str) -> PaymentStatus:
        """Check payment status"""
        token = await self.get_access_token()
        
        response = await self.make_api_request(
            method="GET",
            endpoint=f"/collection/v1_0/requesttopay/{reference_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Target-Environment": "mtnrwanda",
                "Ocp-Apim-Subscription-Key": self.subscription_key
            }
        )
        
        return PaymentStatus(
            status=response.json().get("status"),
            reason=response.json().get("reason")
        )
```

#### C. Airtel Money Integration
```python
class AirtelMoneyService:
    """Airtel Money API Integration"""
    
    async def request_payment(self, phone_number: str, amount: Decimal,
                            transaction_id: str) -> PaymentResult:
        """Initiate payment via Airtel Money"""
        
        # 1. Get Authentication Token
        token = await self.authenticate()
        
        # 2. Prepare Payment Request
        payment_data = {
            "reference": f"SAFEBODA_{transaction_id}",
            "subscriber": {
                "country": "RW",
                "currency": "RWF",
                "msisdn": int(phone_number.replace("+", ""))
            },
            "transaction": {
                "amount": float(amount),
                "country": "RW",
                "currency": "RWF",
                "id": transaction_id
            }
        }
        
        # 3. Make Payment Request
        response = await self.make_api_request(
            method="POST",
            endpoint="/merchant/v1/payments/",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Country": "RW",
                "X-Currency": "RWF"
            },
            data=payment_data
        )
        
        return PaymentResult(
            success=response.json().get("status", {}).get("success", False),
            transaction_id=response.json().get("data", {}).get("transaction", {}).get("id"),
            status="pending"
        )
```

### 2. Driver Payout Flow

#### A. Automatic Payout System
```python
async def process_driver_payout(ride: Ride):
    """Process driver earnings payout"""
    
    # 1. Calculate Driver Earnings
    total_fare = ride.total_fare
    platform_commission = total_fare * Decimal('0.20')  # 20% commission
    driver_earnings = total_fare - platform_commission
    
    # 2. Check Driver Payout Method
    driver_profile = ride.driver.driver_profile
    payout_method = driver_profile.preferred_payout_method
    
    # 3. Process Payout
    if payout_method == 'mtn_momo':
        result = await mtn_disburse_payment(
            phone_number=driver_profile.payout_phone_number,
            amount=driver_earnings,
            reference=f"PAYOUT_{ride.id}"
        )
    elif payout_method == 'airtel_money':
        result = await airtel_disburse_payment(
            phone_number=driver_profile.payout_phone_number,
            amount=driver_earnings,
            reference=f"PAYOUT_{ride.id}"
        )
    else:
        # Add to weekly cash payout
        await add_to_weekly_payout(ride.driver, driver_earnings)
    
    # 4. Record Transaction
    await create_payout_transaction(ride, driver_earnings, result)
```

## Error Handling and Resilience

### 1. Payment Failure Scenarios
```python
class PaymentErrorHandler:
    """Handle payment errors and implement retry logic"""
    
    async def handle_payment_failure(self, payment: Transaction, 
                                   error: Exception) -> None:
        """Handle payment failure with appropriate actions"""
        
        if isinstance(error, NetworkError):
            # Network issues - retry with exponential backoff
            await self.schedule_retry(payment, delay=30)
            
        elif isinstance(error, InsufficientFundsError):
            # Customer has insufficient funds
            await self.notify_customer_insufficient_funds(payment)
            await self.offer_alternative_payment(payment)
            
        elif isinstance(error, InvalidAccountError):
            # Invalid phone number or account
            await self.notify_invalid_account(payment)
            await self.request_account_verification(payment)
            
        elif isinstance(error, ProviderDowntimeError):
            # Provider service unavailable
            await self.switch_to_alternative_provider(payment)
            
        else:
            # Unknown error - log and notify admin
            await self.log_unknown_error(payment, error)
            await self.notify_admin_team(payment, error)
    
    async def schedule_retry(self, payment: Transaction, delay: int):
        """Schedule payment retry with exponential backoff"""
        payment.retry_count += 1
        max_retries = 3
        
        if payment.retry_count <= max_retries:
            # Calculate exponential backoff delay
            retry_delay = delay * (2 ** (payment.retry_count - 1))
            
            # Schedule retry using Celery or similar
            from celery import current_app
            current_app.send_task(
                'payments.retry_payment',
                args=[payment.id],
                countdown=retry_delay
            )
        else:
            # Max retries exceeded - mark as failed
            payment.status = 'failed'
            payment.failure_reason = 'Max retries exceeded'
            await payment.save()
            
            # Notify customer and admin
            await self.notify_payment_failed(payment)
```

### 2. Webhook Processing
```python
class PaymentWebhookHandler:
    """Handle payment status webhooks from providers"""
    
    async def handle_mtn_webhook(self, webhook_data: dict):
        """Process MTN MoMo webhook"""
        reference_id = webhook_data.get('referenceId')
        status = webhook_data.get('status')
        
        # Find corresponding transaction
        transaction = await Transaction.objects.get(
            provider_transaction_id=reference_id
        )
        
        # Update status based on webhook
        if status == 'SUCCESSFUL':
            await self.mark_payment_successful(transaction)
        elif status == 'FAILED':
            await self.mark_payment_failed(transaction, webhook_data.get('reason'))
        
        # Trigger post-payment actions
        await self.trigger_post_payment_actions(transaction)
    
    async def handle_airtel_webhook(self, webhook_data: dict):
        """Process Airtel Money webhook"""
        transaction_id = webhook_data.get('transaction', {}).get('id')
        status = webhook_data.get('transaction', {}).get('status')
        
        transaction = await Transaction.objects.get(
            provider_transaction_id=transaction_id
        )
        
        if status == 'TS':  # Transaction Successful
            await self.mark_payment_successful(transaction)
        elif status == 'TF':  # Transaction Failed
            await self.mark_payment_failed(transaction, 'Payment failed')
```

## Security Implementation

### 1. API Security
```python
class PaymentSecurityManager:
    """Manage payment security and fraud prevention"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=10, window=60)
        self.fraud_detector = FraudDetector()
    
    async def validate_payment_request(self, payment_data: dict, 
                                     user: User) -> ValidationResult:
        """Validate payment request for security"""
        
        # 1. Rate limiting
        if not await self.rate_limiter.allow_request(user.id):
            return ValidationResult(valid=False, reason="Rate limit exceeded")
        
        # 2. Fraud detection
        fraud_score = await self.fraud_detector.calculate_risk_score(
            user=user,
            amount=payment_data['amount'],
            payment_method=payment_data['payment_method']
        )
        
        if fraud_score > 0.8:  # High risk threshold
            await self.flag_suspicious_transaction(payment_data, user)
            return ValidationResult(valid=False, reason="High fraud risk")
        
        # 3. Account verification
        if not await self.verify_payment_account(payment_data):
            return ValidationResult(valid=False, reason="Invalid account")
        
        return ValidationResult(valid=True)
    
    async def encrypt_sensitive_data(self, data: dict) -> dict:
        """Encrypt sensitive payment data"""
        encrypted_data = data.copy()
        
        # Encrypt phone numbers
        if 'phone_number' in data:
            encrypted_data['phone_number'] = await self.encrypt_field(
                data['phone_number']
            )
        
        # Encrypt account details
        if 'account_details' in data:
            encrypted_data['account_details'] = await self.encrypt_field(
                json.dumps(data['account_details'])
            )
        
        return encrypted_data
```

### 2. Transaction Monitoring
```python
class TransactionMonitor:
    """Monitor transactions for anomalies and compliance"""
    
    async def monitor_transaction(self, transaction: Transaction):
        """Real-time transaction monitoring"""
        
        # 1. Amount validation
        if transaction.amount > Decimal('100000'):  # > 100k RWF
            await self.flag_large_transaction(transaction)
        
        # 2. Velocity checks
        recent_transactions = await self.get_recent_transactions(
            user=transaction.from_user,
            minutes=60
        )
        
        if len(recent_transactions) > 10:
            await self.flag_high_velocity(transaction)
        
        # 3. Geographic anomaly
        if await self.detect_geographic_anomaly(transaction):
            await self.flag_geographic_anomaly(transaction)
        
        # 4. Government reporting (for large amounts)
        if transaction.amount > Decimal('1000000'):  # > 1M RWF
            await self.report_to_bnr(transaction)  # Bank of Rwanda
```

## Rwanda-Specific Compliance

### 1. Bank of Rwanda (BNR) Reporting
```python
class BNRComplianceService:
    """Handle Bank of Rwanda compliance reporting"""
    
    async def generate_monthly_report(self, month: int, year: int):
        """Generate monthly transaction report for BNR"""
        
        transactions = await Transaction.objects.filter(
            created_at__month=month,
            created_at__year=year,
            status='completed'
        ).all()
        
        report_data = {
            'reporting_period': f"{year}-{month:02d}",
            'total_transactions': len(transactions),
            'total_volume': sum(t.amount for t in transactions),
            'transaction_breakdown': {
                'mtn_momo': await self.calculate_provider_stats(transactions, 'mtn_momo'),
                'airtel_money': await self.calculate_provider_stats(transactions, 'airtel_money'),
                'cash': await self.calculate_provider_stats(transactions, 'cash')
            },
            'large_transactions': [
                t for t in transactions if t.amount > Decimal('1000000')
            ]
        }
        
        # Submit to BNR reporting system
        await self.submit_to_bnr(report_data)
```

### 2. Tax Compliance
```python
class RwandaTaxService:
    """Handle Rwanda Revenue Authority (RRA) tax compliance"""
    
    async def calculate_transaction_tax(self, transaction: Transaction) -> Decimal:
        """Calculate applicable taxes for transaction"""
        
        base_amount = transaction.amount
        vat_rate = Decimal('0.18')  # 18% VAT
        
        # Service fee is subject to VAT
        service_fee = base_amount * Decimal('0.20')  # 20% commission
        vat_amount = service_fee * vat_rate
        
        return vat_amount
    
    async def generate_vat_return(self, quarter: int, year: int):
        """Generate quarterly VAT return"""
        
        start_date = datetime(year, (quarter-1)*3+1, 1)
        end_date = datetime(year, quarter*3, 1)
        
        transactions = await Transaction.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date,
            status='completed'
        ).all()
        
        total_vat = sum(
            await self.calculate_transaction_tax(t) for t in transactions
        )
        
        # Submit to RRA system
        await self.submit_vat_return(quarter, year, total_vat)
```

## Performance Optimization

### 1. Caching Strategy
```python
class PaymentCacheManager:
    """Manage payment-related caching"""
    
    def __init__(self):
        self.redis_client = redis.Redis()
        self.default_ttl = 300  # 5 minutes
    
    async def cache_payment_method(self, user_id: str, payment_methods: list):
        """Cache user's payment methods"""
        cache_key = f"payment_methods:{user_id}"
        await self.redis_client.setex(
            cache_key,
            self.default_ttl,
            json.dumps(payment_methods)
        )
    
    async def cache_provider_status(self, provider: str, status: dict):
        """Cache payment provider status"""
        cache_key = f"provider_status:{provider}"
        await self.redis_client.setex(
            cache_key,
            60,  # 1 minute
            json.dumps(status)
        )
```

### 2. Async Processing
```python
# Celery tasks for async payment processing
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def process_payment_async(self, payment_id: str):
    """Process payment asynchronously"""
    try:
        payment = Transaction.objects.get(id=payment_id)
        service = PaymentProcessingService()
        result = service.process_payment(payment)
        
        if not result.success:
            raise PaymentProcessingError(result.error_message)
            
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task
def send_payment_notifications(transaction_id: str, event_type: str):
    """Send payment-related notifications"""
    transaction = Transaction.objects.get(id=transaction_id)
    notification_service = NotificationService()
    
    notification_service.send_payment_notification(
        transaction=transaction,
        event_type=event_type
    )
```

## API Endpoints Documentation

### 1. Payment Processing
```yaml
# POST /api/payments/process/
requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        properties:
          ride_id:
            type: string
            format: uuid
          payment_method:
            type: string
            enum: [mtn_momo, airtel_money, cash]
          phone_number:
            type: string
            pattern: '^\+250[0-9]{9}$'
          amount:
            type: number
            minimum: 500
            maximum: 100000
        required:
          - ride_id
          - payment_method
          - amount

responses:
  '201':
    description: Payment initiated successfully
    content:
      application/json:
        schema:
          type: object
          properties:
            success:
              type: boolean
            transaction_id:
              type: string
              format: uuid
            status:
              type: string
              enum: [pending, processing, completed, failed]
            provider_reference:
              type: string
            estimated_completion:
              type: string
              format: date-time
```

## Testing Strategy

### 1. Unit Tests
```python
class TestPaymentProcessing(TestCase):
    """Test payment processing functionality"""
    
    async def test_mtn_payment_success(self):
        """Test successful MTN payment processing"""
        # Mock MTN API responses
        with patch('payments.services.MTNMoMoService.request_payment') as mock_payment:
            mock_payment.return_value = PaymentResult(
                success=True,
                transaction_id="test-ref-123",
                status="pending"
            )
            
            service = PaymentProcessingService()
            result = await service.process_payment(self.test_transaction)
            
            self.assertTrue(result.success)
            self.assertEqual(result.status, "pending")
    
    async def test_payment_failure_retry(self):
        """Test payment failure and retry logic"""
        with patch('payments.services.MTNMoMoService.request_payment') as mock_payment:
            mock_payment.side_effect = NetworkError("Connection timeout")
            
            service = PaymentProcessingService()
            result = await service.process_payment(self.test_transaction)
            
            # Should schedule retry
            self.assertEqual(self.test_transaction.retry_count, 1)
```

### 2. Integration Tests
```python
class TestPaymentIntegration(TransactionTestCase):
    """Test payment system integration"""
    
    def test_end_to_end_payment_flow(self):
        """Test complete payment workflow"""
        # 1. Create ride
        ride = self.create_test_ride()
        
        # 2. Initiate payment
        response = self.client.post('/api/payments/process/', {
            'ride_id': str(ride.id),
            'payment_method': 'mtn_momo',
            'phone_number': '+250788123456',
            'amount': ride.total_fare
        })
        
        self.assertEqual(response.status_code, 201)
        
        # 3. Simulate webhook callback
        webhook_data = {
            'referenceId': response.json()['provider_reference'],
            'status': 'SUCCESSFUL'
        }
        
        webhook_response = self.client.post('/api/payments/webhooks/mtn/', webhook_data)
        self.assertEqual(webhook_response.status_code, 200)
        
        # 4. Verify final state
        ride.refresh_from_db()
        self.assertEqual(ride.payment_status, 'completed')
```

This comprehensive payment workflow documentation covers all aspects of the Rwanda mobile money integration, from API design to security, compliance, and testing strategies.