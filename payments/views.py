"""
Payment views for SafeBoda Rwanda
Handles mobile money integration and payment processing
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils import timezone
from .models import Transaction, PaymentMethod, MobileMoneyAccount
from .serializers import (
    PaymentProcessSerializer, TransactionSerializer, PaymentMethodSerializer,
    PaymentResponseSerializer, MobileMoneyAccountSerializer
)
from .services import PaymentProcessingService, MobileMoneyService, MTNMoMoService, AirtelMoneyService
from bookings.models import Ride
import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    post=extend_schema(
        summary="Process payment",
        description="Process payment for ride or other services using Rwanda mobile money",
        tags=['Payments']
    )
)
class ProcessPaymentView(APIView):
    """
    POST /api/payments/process/ - Process payment (design implementation)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Process payment using mobile money or other methods"""
        serializer = PaymentProcessSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid payment data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Initialize payment service
            payment_service = PaymentProcessingService()
            
            # Process payment
            payment_result = payment_service.process_payment(
                user=request.user,
                amount=serializer.validated_data['amount'],
                provider=serializer.validated_data['provider'],
                phone_number=serializer.validated_data.get('phone_number'),
                description=serializer.validated_data.get('description', ''),
                ride_id=serializer.validated_data.get('ride_id')
            )
            
            if payment_result['success']:
                response_serializer = PaymentResponseSerializer(payment_result)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Payment failed', 'details': payment_result.get('error')},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'error': 'Payment processing error', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    post=extend_schema(
        summary="Process payment",
        description="Process payment for ride using Rwanda mobile money or other methods",
        tags=['Payments']
    )
)
class ProcessPaymentView(APIView):
    """
    POST /api/payments/process/ - Process payment (design only for assignment)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        ride = data['ride']
        payment_method = data['payment_method']
        amount = data['amount']
        
        # Initialize payment processing service
        payment_service = PaymentProcessingService()
        
        try:
            # Process payment based on method
            if payment_method == 'mtn_momo':
                result = payment_service.process_mtn_payment(
                    ride, amount, data.get('phone_number')
                )
            elif payment_method == 'airtel_money':
                result = payment_service.process_airtel_payment(
                    ride, amount, data.get('phone_number')
                )
            elif payment_method == 'cash':
                result = payment_service.process_cash_payment(ride, amount)
            else:
                return Response({
                    'error': 'Unsupported payment method'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if result['success']:
                logger.info(f"Payment processed successfully for ride {ride.id}")
                return Response({
                    'message': 'Payment processed successfully',
                    'transaction_id': result['transaction_id'],
                    'status': result['status']
                })
            else:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Payment processing error: {str(e)}")
            return Response({
                'error': 'Payment processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    get=extend_schema(
        summary="Get payment history",
        description="Retrieve user's payment transaction history",
        tags=['Payments']
    )
)
class PaymentHistoryView(generics.ListAPIView):
    """
    GET /api/payments/history/ - Payment history
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'admin':
            return Transaction.objects.all().order_by('-created_at')
        elif user.role == 'driver':
            # Drivers see payments they received
            return Transaction.objects.filter(
                to_user=user
            ).order_by('-created_at')
        else:
            # Customers see payments they made
            return Transaction.objects.filter(
                from_user=user
            ).order_by('-created_at')


@extend_schema_view(
    get=extend_schema(
        summary="Get payment methods",
        description="Get user's saved payment methods",
        tags=['Payments']
    ),
    post=extend_schema(
        summary="Add payment method",
        description="Add new payment method for user",
        tags=['Payments']
    )
)
class PaymentMethodView(generics.ListCreateAPIView):
    """
    Manage user payment methods
    """
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(
            user=self.request.user,
            is_active=True
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    get=extend_schema(
        summary="Get mobile money accounts",
        description="Get user's verified mobile money accounts",
        tags=['Payments']
    ),
    post=extend_schema(
        summary="Add mobile money account",
        description="Add and verify mobile money account",
        tags=['Payments']
    )
)
class MobileMoneyAccountView(generics.ListCreateAPIView):
    """
    Manage mobile money accounts
    """
    serializer_class = MobileMoneyAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return MobileMoneyAccount.objects.filter(
            user=self.request.user,
            is_active=True
        )
    
    def perform_create(self, serializer):
        account = serializer.save(user=self.request.user)
        
        # Initiate verification process
        verification_service = PaymentProcessingService()
        verification_service.verify_mobile_money_account(account)


@extend_schema(
    summary="Initiate MTN Mobile Money payment",
    description="Initiate MTN Mobile Money payment (Rwanda-specific implementation)",
    tags=['Payments', 'Rwanda Mobile Money']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def initiate_mtn_payment(request):
    """
    Rwanda MTN Mobile Money integration
    """
    phone_number = request.data.get('phone_number')
    amount = request.data.get('amount')
    ride_id = request.data.get('ride_id')
    
    if not all([phone_number, amount, ride_id]):
        return Response({
            'error': 'Missing required fields'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ride = Ride.objects.get(pk=ride_id, customer=request.user)
    except Ride.DoesNotExist:
        return Response({
            'error': 'Ride not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Initialize MTN MoMo service
    mtn_service = MTNMoMoService()
    
    try:
        result = mtn_service.request_payment(
            phone_number=phone_number,
            amount=amount,
            external_id=str(ride.id),
            payer_message=f"SafeBoda ride payment",
            payee_note=f"Payment for ride {ride.id}"
        )
        
        if result['success']:
            # Create transaction record
            transaction = Transaction.objects.create(
                transaction_type='ride_payment',
                from_user=request.user,
                to_user=ride.driver,
                amount=amount,
                provider='mtn_momo',
                provider_transaction_id=result['transaction_id'],
                ride=ride,
                description=f"MTN MoMo payment for ride {ride.id}"
            )
            
            return Response({
                'message': 'Payment initiated successfully',
                'transaction_id': str(transaction.id),
                'provider_reference': result['transaction_id'],
                'status': 'processing'
            })
        else:
            return Response({
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"MTN MoMo payment error: {str(e)}")
        return Response({
            'error': 'Payment initiation failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Initiate Airtel Money payment",
    description="Initiate Airtel Money payment (Rwanda-specific implementation)",
    tags=['Payments', 'Rwanda Mobile Money']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def initiate_airtel_payment(request):
    """
    Rwanda Airtel Money integration
    """
    phone_number = request.data.get('phone_number')
    amount = request.data.get('amount')
    ride_id = request.data.get('ride_id')
    
    if not all([phone_number, amount, ride_id]):
        return Response({
            'error': 'Missing required fields'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ride = Ride.objects.get(pk=ride_id, customer=request.user)
    except Ride.DoesNotExist:
        return Response({
            'error': 'Ride not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Initialize Airtel Money service
    airtel_service = AirtelMoneyService()
    
    try:
        result = airtel_service.request_payment(
            phone_number=phone_number,
            amount=amount,
            transaction_id=str(ride.id),
            reference=f"SafeBoda-{ride.id}"
        )
        
        if result['success']:
            # Create transaction record
            transaction = Transaction.objects.create(
                transaction_type='ride_payment',
                from_user=request.user,
                to_user=ride.driver,
                amount=amount,
                provider='airtel_money',
                provider_transaction_id=result['transaction_id'],
                ride=ride,
                description=f"Airtel Money payment for ride {ride.id}"
            )
            
            return Response({
                'message': 'Payment initiated successfully',
                'transaction_id': str(transaction.id),
                'provider_reference': result['transaction_id'],
                'status': 'processing'
            })
        else:
            return Response({
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Airtel Money payment error: {str(e)}")
        return Response({
            'error': 'Payment initiation failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Check payment status",
    description="Check status of mobile money payment transaction",
    tags=['Payments']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_payment_status(request, transaction_id):
    """
    Check payment status
    """
    try:
        transaction = Transaction.objects.get(
            id=transaction_id,
            from_user=request.user
        )
    except Transaction.DoesNotExist:
        return Response({
            'error': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check status with provider
    payment_service = PaymentProcessingService()
    
    try:
        if transaction.provider == 'mtn_momo':
            status_result = payment_service.check_mtn_status(transaction)
        elif transaction.provider == 'airtel_money':
            status_result = payment_service.check_airtel_status(transaction)
        else:
            status_result = {'status': transaction.status}
        
        return Response({
            'transaction_id': str(transaction.id),
            'status': status_result['status'],
            'provider_reference': transaction.provider_transaction_id,
            'amount': transaction.amount,
            'created_at': transaction.created_at
        })
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return Response({
            'error': 'Unable to check payment status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)