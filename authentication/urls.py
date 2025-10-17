"""
Authentication URL patterns for SafeBoda Rwanda
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'authentication'

urlpatterns = [
    # User Authentication
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    
    # Driver Profile
    path('driver/profile/', views.DriverProfileView.as_view(), name='driver_profile'),
    
    # Verification
    path('verify/', views.verify_code, name='verify_code'),
    path('resend-code/', views.resend_verification_code, name='resend_code'),
    
    # Password Management
    path('password/reset/', views.password_reset_request, name='password_reset'),
    path('password/confirm/', views.password_reset_confirm, name='password_confirm'),
    path('password/change/', views.change_password, name='change_password'),
]