"""
URL configuration for payments app
"""
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment processing endpoints
    path('process/', views.ProcessPaymentView.as_view(), name='process-payment'),
    
    # Payment method management
    path('methods/', views.PaymentMethodView.as_view(), name='payment-methods'),
    path('accounts/', views.MobileMoneyAccountView.as_view(), name='momo-accounts'),
    
    # Transaction management
    path('history/', views.PaymentHistoryView.as_view(), name='payment-history'),
    
    # Rwanda mobile money endpoints
    path('mtn/initiate/', views.initiate_mtn_payment, name='mtn-initiate'),
    path('airtel/initiate/', views.initiate_airtel_payment, name='airtel-initiate'),
    path('status/<uuid:transaction_id>/', views.check_payment_status, name='payment-status'),
]