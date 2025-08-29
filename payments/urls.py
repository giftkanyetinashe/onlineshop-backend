# payments/urls.py
from django.urls import path
from .views import InitiatePaymentView, PaynowUpdateView, CheckPaymentStatusView, test_connection_view , PayPalCreateOrderView, PayPalCaptureOrderView

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('update/', PaynowUpdateView.as_view(), name='paynow-update'),
    path('status/<str:reference>/', CheckPaymentStatusView.as_view(), name='check-payment-status'),

    path('test-connection/', test_connection_view, name='test-connection'),

    path('paypal/create/', PayPalCreateOrderView.as_view(), name='paypal-create-order'),
    path('paypal/capture/', PayPalCaptureOrderView.as_view(), name='paypal-capture-order'),

]