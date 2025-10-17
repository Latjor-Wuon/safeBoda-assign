"""
Payment models for SafeBoda Rwanda
Handles mobile money integration, transactions, and Rwanda-specific payment methods
"""
from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
import uuid

User = get_user_model()


class PaymentMethod(models.Model):
    """
    User payment methods including Rwanda mobile money
    """
    PROVIDER_CHOICES = (
        ('mtn_momo', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('bank_card', 'Bank Card'),
        ('cash', 'Cash'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    
    # Mobile money details
    phone_number = models.CharField(max_length=15, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    
    # Card details (encrypted)
    masked_card_number = models.CharField(max_length=19, blank=True)
    card_holder_name = models.CharField(max_length=100, blank=True)
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_methods'
        unique_together = ['user', 'provider', 'phone_number']


class Transaction(models.Model):
    """
    All payment transactions for rides and other services
    """
    TRANSACTION_TYPES = (
        ('ride_payment', 'Ride Payment'),
        ('wallet_topup', 'Wallet Top-up'),
        ('refund', 'Refund'),
        ('withdrawal', 'Driver Withdrawal'),
        ('commission', 'Platform Commission'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Parties involved
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outgoing_transactions', null=True, blank=True)
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incoming_transactions', null=True, blank=True)
    
    # Amount details (in RWF)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='RWF')
    
    # Mobile money integration
    provider = models.CharField(max_length=20, choices=PaymentMethod.PROVIDER_CHOICES)
    provider_transaction_id = models.CharField(max_length=100, blank=True)
    provider_reference = models.CharField(max_length=100, blank=True)
    
    # Rwanda tax information
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Metadata
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Related objects
    ride = models.ForeignKey('bookings.Ride', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['from_user', 'status']),
            models.Index(fields=['to_user', 'status']),
            models.Index(fields=['provider_transaction_id']),
            models.Index(fields=['created_at']),
        ]


class MobileMoneyAccount(models.Model):
    """
    Rwanda mobile money account integration
    """
    PROVIDER_CHOICES = (
        ('mtn', 'MTN Rwanda'),
        ('airtel', 'Airtel Rwanda'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='momo_accounts')
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES)
    phone_number = models.CharField(max_length=15)
    account_holder_name = models.CharField(max_length=100)
    
    # Verification status
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Balance tracking (optional, for wallet feature)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    last_balance_update = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mobile_money_accounts'
        unique_together = ['provider', 'phone_number']