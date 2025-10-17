"""
Payment serializers for SafeBoda Rwanda
"""
from rest_framework import serializers
from .models import PaymentMethod, Transaction, MobileMoneyAccount
from decimal import Decimal


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'provider', 'phone_number', 'account_name',
            'is_default', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions"""
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_type', 'status', 'amount', 'currency',
            'provider', 'provider_transaction_id', 'description',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']


class PaymentProcessSerializer(serializers.Serializer):
    """Serializer for processing payments"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    provider = serializers.ChoiceField(choices=PaymentMethod.PROVIDER_CHOICES)
    phone_number = serializers.CharField(max_length=15, required=False)
    description = serializers.CharField(max_length=255, required=False)
    ride_id = serializers.UUIDField(required=False)


class PaymentResponseSerializer(serializers.Serializer):
    """Serializer for payment response"""
    success = serializers.BooleanField()
    transaction_id = serializers.UUIDField(required=False)
    provider_transaction_id = serializers.CharField(required=False)
    status = serializers.CharField()
    message = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class MobileMoneyAccountSerializer(serializers.ModelSerializer):
    """Serializer for mobile money accounts"""
    
    class Meta:
        model = MobileMoneyAccount
        fields = [
            'id', 'provider', 'phone_number', 'account_holder_name',
            'is_verified', 'current_balance', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'is_verified', 'current_balance', 'created_at']