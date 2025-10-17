"""
Authentication serializers for SafeBoda Rwanda
Handles user registration, login, and profile management with Rwanda-specific validation
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
# from phonenumber_field.serializerfields import PhoneNumberField
from .models import User, DriverProfile, VerificationCode
import re


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    User registration with Rwanda-specific validations
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(max_length=15)
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'password_confirm',
            'phone_number', 'first_name', 'last_name', 'middle_name',
            'national_id', 'date_of_birth', 'gender', 'role',
            'province', 'district', 'sector', 'cell', 'village',
            'language_preference'
        ]
        extra_kwargs = {
            'national_id': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': True},
        }
    
    def validate_password_confirm(self, value):
        if value != self.initial_data.get('password'):
            raise serializers.ValidationError("Passwords do not match.")
        return value
    
    def validate_national_id(self, value):
        """Validate Rwanda National ID format"""
        if not re.match(r'^\d{16}$', value):
            raise serializers.ValidationError(
                "Rwanda National ID must be exactly 16 digits."
            )
        
        # Check if already exists
        if User.objects.filter(national_id=value).exists():
            raise serializers.ValidationError(
                "A user with this National ID already exists."
            )
        
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number is Rwanda number"""
        if not str(value).startswith('+250'):
            raise serializers.ValidationError(
                "Please provide a valid Rwanda phone number starting with +250"
            )
        return value
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value.lower()
    
    def validate_role(self, value):
        """Validate user role"""
        if value not in ['customer', 'driver']:
            raise serializers.ValidationError(
                "Role must be either 'customer' or 'driver' during registration."
            )
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Send verification codes
        self._send_verification_codes(user)
        
        return user
    
    def _send_verification_codes(self, user):
        """Send phone and email verification codes"""
        # This would integrate with actual SMS/Email services
        # For now, we'll just create the codes in database
        from django.utils import timezone
        from datetime import timedelta
        import random
        
        # Phone verification
        phone_code = f"{random.randint(100000, 999999)}"
        VerificationCode.objects.create(
            user=user,
            code=phone_code,
            verification_type='phone',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Email verification
        email_code = f"{random.randint(100000, 999999)}"
        VerificationCode.objects.create(
            user=user,
            code=email_code,
            verification_type='email',
            expires_at=timezone.now() + timedelta(hours=24)
        )


class UserLoginSerializer(TokenObtainPairSerializer):
    """
    Enhanced JWT login with user details
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['user_id'] = str(user.id)
        token['role'] = user.role
        token['full_name'] = user.full_name
        token['is_verified'] = user.is_verified
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user information to response
        user = self.user
        data.update({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role,
                'phone_number': str(user.phone_number),
                'is_verified': user.is_verified,
                'is_phone_verified': user.is_phone_verified,
                'is_email_verified': user.is_email_verified,
                'language_preference': user.language_preference,
            }
        })
        
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer for viewing and updating
    """
    phone_number = serializers.CharField(max_length=15)
    full_name = serializers.ReadOnlyField()
    rwanda_address = serializers.ReadOnlyField(source='get_rwanda_address')
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'full_name',
            'first_name', 'last_name', 'middle_name',
            'phone_number', 'national_id', 'date_of_birth', 'gender',
            'province', 'district', 'sector', 'cell', 'village',
            'rwanda_address', 'profile_picture', 'language_preference',
            'role', 'is_verified', 'is_phone_verified', 'is_email_verified',
            'created_at', 'last_login'
        ]
        read_only_fields = [
            'id', 'email', 'national_id', 'role', 'is_verified',
            'is_phone_verified', 'is_email_verified', 'created_at', 'last_login'
        ]


class DriverProfileSerializer(serializers.ModelSerializer):
    """
    Driver profile serializer with vehicle and license information
    """
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = DriverProfile
        fields = [
            'user', 'license_number', 'license_expiry_date', 'license_category',
            'vehicle_type', 'vehicle_plate_number', 'vehicle_make', 'vehicle_model',
            'vehicle_year', 'vehicle_color', 'insurance_number', 'insurance_expiry_date',
            'vehicle_inspection_date', 'vehicle_inspection_expiry', 'status',
            'rating', 'total_rides', 'total_earnings', 'is_online',
            'created_at', 'approved_at'
        ]
        read_only_fields = [
            'status', 'rating', 'total_rides', 'total_earnings',
            'created_at', 'approved_at'
        ]
    
    def validate_license_number(self, value):
        """Validate Rwanda driver license format"""
        if not re.match(r'^[A-Z0-9]{8,20}$', value):
            raise serializers.ValidationError(
                "Invalid Rwanda driver license format"
            )
        return value
    
    def validate_vehicle_plate_number(self, value):
        """Validate Rwanda vehicle plate number"""
        # Remove spaces and convert to uppercase
        plate = value.replace(' ', '').upper()
        
        if not re.match(r'^R[A-Z]{2}\d{3}[A-Z]$', plate):
            raise serializers.ValidationError(
                "Invalid Rwanda vehicle plate number format. Should be like 'RAA 123A'"
            )
        
        return plate


class VerifyCodeSerializer(serializers.Serializer):
    """
    Verification code validation
    """
    code = serializers.CharField(max_length=6, min_length=6)
    verification_type = serializers.ChoiceField(choices=['phone', 'email'])
    
    def validate_code(self, value):
        """Validate verification code"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must contain only digits")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Password reset request
    """
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Check if user exists with this email"""
        try:
            User.objects.get(email=value.lower())
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No user found with this email address"
            )
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Password reset confirmation with new password
    """
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    
    def validate_confirm_password(self, value):
        if value != self.initial_data.get('new_password'):
            raise serializers.ValidationError("Passwords do not match")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Change password for authenticated users
    """
    current_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value
    
    def validate_confirm_password(self, value):
        if value != self.initial_data.get('new_password'):
            raise serializers.ValidationError("Passwords do not match")
        return value