"""
Authentication views for SafeBoda Rwanda
Implements JWT authentication, user registration, and profile management
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import DriverProfile, VerificationCode
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    DriverProfileSerializer, VerifyCodeSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, ChangePasswordSerializer
)
from .permissions import IsOwnerOrReadOnly, IsDriverUser, IsAdminOrDriver
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@extend_schema_view(
    post=extend_schema(
        summary="Register new user",
        description="Register a new customer or driver account with Rwanda-specific validation",
        tags=['Authentication']
    )
)
class UserRegistrationView(generics.CreateAPIView):
    """
    Register new users (customers and drivers)
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Log registration
        logger.info(f"New user registered: {user.email} (Role: {user.role})")
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful. Please verify your phone number and email.'
        }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        summary="User login",
        description="Authenticate user and return JWT tokens with user information",
        tags=['Authentication']
    )
)
class UserLoginView(TokenObtainPairView):
    """
    Enhanced JWT login with user information
    """
    serializer_class = UserLoginSerializer
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Update last login IP
            user_email = request.data.get('email')
            try:
                user = User.objects.get(email=user_email)
                user.last_login_ip = self.get_client_ip(request)
                user.save(update_fields=['last_login_ip'])
                
                logger.info(f"User login successful: {user.email}")
            except User.DoesNotExist:
                pass
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema_view(
    post=extend_schema(
        summary="Logout user",
        description="Logout user and blacklist refresh token",
        tags=['Authentication']
    )
)
class UserLogoutView(APIView):
    """
    Logout user by blacklisting refresh token
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            logger.info(f"User logout: {request.user.email}")
            
            return Response({
                'message': 'Successfully logged out'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        summary="Get user profile",
        description="Retrieve current user's profile information",
        tags=['Authentication']
    ),
    put=extend_schema(
        summary="Update user profile",
        description="Update current user's profile information",
        tags=['Authentication']
    ),
    patch=extend_schema(
        summary="Partially update user profile",
        description="Partially update current user's profile information",
        tags=['Authentication']
    )
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update user profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        logger.info(f"Profile update request from: {request.user.email}")
        return super().update(request, *args, **kwargs)


@extend_schema_view(
    get=extend_schema(
        summary="Get driver profile",
        description="Retrieve driver profile with vehicle information",
        tags=['Authentication', 'Drivers']
    ),
    put=extend_schema(
        summary="Update driver profile",
        description="Update driver profile and vehicle information",
        tags=['Authentication', 'Drivers']
    ),
    post=extend_schema(
        summary="Create driver profile",
        description="Create driver profile for existing user",
        tags=['Authentication', 'Drivers']
    )
)
class DriverProfileView(generics.RetrieveUpdateAPIView):
    """
    Driver profile management
    """
    serializer_class = DriverProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriverUser]
    
    def get_object(self):
        try:
            return self.request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return None
    
    def create(self, request, *args, **kwargs):
        # Check if driver profile already exists
        if hasattr(request.user, 'driver_profile'):
            return Response({
                'error': 'Driver profile already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user role is driver
        if request.user.role != 'driver':
            return Response({
                'error': 'User must have driver role to create driver profile'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        driver_profile = serializer.save(user=request.user)
        
        logger.info(f"Driver profile created: {request.user.email}")
        
        return Response(
            DriverProfileSerializer(driver_profile).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(
    summary="Verify phone or email",
    description="Verify phone number or email with verification code",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_code(request):
    """
    Verify phone number or email with verification code
    """
    serializer = VerifyCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    code = serializer.validated_data['code']
    verification_type = serializer.validated_data['verification_type']
    
    try:
        verification = VerificationCode.objects.get(
            user=request.user,
            code=code,
            verification_type=verification_type,
            is_used=False,
            expires_at__gt=timezone.now()
        )
        
        # Mark as used
        verification.is_used = True
        verification.used_at = timezone.now()
        verification.save()
        
        # Update user verification status
        if verification_type == 'phone':
            request.user.is_phone_verified = True
        elif verification_type == 'email':
            request.user.is_email_verified = True
        
        # Check if user is fully verified
        if request.user.is_phone_verified and request.user.is_email_verified:
            request.user.is_verified = True
        
        request.user.save()
        
        logger.info(f"Verification successful: {request.user.email} ({verification_type})")
        
        return Response({
            'message': f'{verification_type.title()} verified successfully',
            'is_verified': request.user.is_verified
        })
        
    except VerificationCode.DoesNotExist:
        return Response({
            'error': 'Invalid or expired verification code'
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Resend verification code",
    description="Resend verification code for phone or email",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resend_verification_code(request):
    """
    Resend verification code
    """
    verification_type = request.data.get('verification_type')
    
    if verification_type not in ['phone', 'email']:
        return Response({
            'error': 'Invalid verification type'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if already verified
    if verification_type == 'phone' and request.user.is_phone_verified:
        return Response({
            'error': 'Phone number is already verified'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if verification_type == 'email' and request.user.is_email_verified:
        return Response({
            'error': 'Email is already verified'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create new verification code
    from datetime import timedelta
    import random
    
    code = f"{random.randint(100000, 999999)}"
    expires_at = timezone.now() + timedelta(minutes=10)
    
    VerificationCode.objects.create(
        user=request.user,
        code=code,
        verification_type=verification_type,
        expires_at=expires_at
    )
    
    # Here you would send the actual SMS/Email
    # For now, just log it
    logger.info(f"Verification code sent: {request.user.email} ({verification_type}): {code}")
    
    return Response({
        'message': f'Verification code sent to your {verification_type}'
    })


@extend_schema(
    summary="Request password reset",
    description="Request password reset code via email",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """
    Request password reset
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    
    try:
        user = User.objects.get(email=email)
        
        # Create password reset code
        from datetime import timedelta
        import random
        
        code = f"{random.randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(hours=1)
        
        VerificationCode.objects.create(
            user=user,
            code=code,
            verification_type='password_reset',
            expires_at=expires_at
        )
        
        # Send email (log for now)
        logger.info(f"Password reset code sent: {email}: {code}")
        
        return Response({
            'message': 'Password reset code sent to your email'
        })
        
    except User.DoesNotExist:
        # Don't reveal if email exists or not
        return Response({
            'message': 'If the email exists, a reset code has been sent'
        })


@extend_schema(
    summary="Confirm password reset",
    description="Reset password with verification code",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """
    Confirm password reset with code
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    code = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']
    
    try:
        verification = VerificationCode.objects.get(
            code=code,
            verification_type='password_reset',
            is_used=False,
            expires_at__gt=timezone.now()
        )
        
        # Update password
        user = verification.user
        user.set_password(new_password)
        user.save()
        
        # Mark verification as used
        verification.is_used = True
        verification.used_at = timezone.now()
        verification.save()
        
        logger.info(f"Password reset successful: {user.email}")
        
        return Response({
            'message': 'Password reset successful'
        })
        
    except VerificationCode.DoesNotExist:
        return Response({
            'error': 'Invalid or expired reset code'
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Change password",
    description="Change password for authenticated user",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """
    Change password for authenticated user
    """
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    new_password = serializer.validated_data['new_password']
    
    request.user.set_password(new_password)
    request.user.save()
    
    logger.info(f"Password changed: {request.user.email}")
    
    return Response({
        'message': 'Password changed successfully'
    })