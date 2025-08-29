# payments/views.py

import hashlib
import requests
import uuid
from urllib.parse import urlencode, unquote
from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
# IMPORTANT: Import your Order model. Adjust the path if needed.
from orders.models import Order
from rest_framework.permissions import AllowAny


# --- Helper function to generate the hash ---
def generate_hash(values_string, integration_key):
    """Generates the SHA512 hash required by Paynow."""
    full_string = values_string + integration_key
    sha512 = hashlib.sha512()
    sha512.update(full_string.encode('utf-8'))
    return sha512.hexdigest().upper()


def test_connection_view(request):
    """A simple view to test if the server is accessible from the internet."""
    return HttpResponse("Connection OK! Your Django server is visible.", status=200)


class InitiatePaymentView(APIView):
    
    """
    Takes an `order_id` from the frontend to initiate a payment.
    This is more secure as the amount and description are pulled from the
    trusted order object on the server, not from the client request.
    """
    def post(self, request, *args, **kwargs):
        # 1. Get order_id from the React frontend's request body
        order_id = request.data.get('order_id')

        if not order_id:
            return Response(
                {'error': 'order_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. SERVER-SIDE VALIDATION: Find the order
        try:
            # Note: Your Order model might use 'id', 'pk', or a UUID field. Adjust accordingly.
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Invalid order_id. Order not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Optional: Check if the order is already paid to prevent double payments
        if order.payment_status == 'PAID': # Assuming you have a 'payment_status' field
            return Response(
                {'error': 'This order has already been paid for.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Create a unique reference for this specific payment attempt
        payment_reference = f"ORDER-{order.order_number}-{uuid.uuid4().hex[:4].upper()}"

        # 4. Create the payment record in your database, linked to the order
        payment = Payment.objects.create(
            order=order,
            reference=payment_reference,
            amount=order.total_price,  # Use total_price, not total_amount
            description=f"Payment for Order #{order.order_number}",
            status=Payment.PaymentStatus.PENDING,
        )

        # 5. Prepare the payload to send to Paynow
        # IMPORTANT: Replace this with your actual, live tunnel URL from ngrok/cloudflare
        active_tunnel_url = "https://dodge-shield-low-jaguar.trycloudflare.com"

        payload = {
            'id': settings.PAYNOW_INTEGRATION_ID,
            'reference': payment.reference,
            'amount': str(payment.amount),
            'additionalinfo': payment.description,
            'returnurl': f'http://localhost:3000/payment-status?reference={payment.reference}',
            'resulturl': f'{active_tunnel_url}/api/api/payments/update/',
            'status': 'Message',
        }

        # Create the hash for the INITIATION request
        values_string = "".join(str(v) for v in payload.values())
        payload['hash'] = generate_hash(values_string, settings.PAYNOW_INTEGRATION_KEY)

        # 6. Send the request to Paynow
        print(f"Sending initiation request to Paynow for reference: {payment.reference}")
        response = requests.post(settings.PAYNOW_INITIATE_TRANSACTION_URL, data=payload)

        if not response.ok:
            payment.status = Payment.PaymentStatus.FAILED
            payment.save()
            return Response({'error': 'Failed to connect to Paynow.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 7. Process the response from Paynow
        response_data = dict(item.split('=', 1) for item in response.text.split('&'))
        status_from_paynow = response_data.get('status', '').lower()

        if status_from_paynow == 'ok':
            redirect_url_encoded = response_data.get('browserurl')
            payment.paynow_reference = response_data.get('paynowreference')
            payment.save()

            print(f"Successfully initiated. Redirecting user to: {unquote(redirect_url_encoded)}")
            return Response({
                'redirect_url': unquote(redirect_url_encoded),
            }, status=status.HTTP_200_OK)
        else:
            error_message = unquote(response_data.get('error', 'Unknown error from Paynow.'))
            payment.status = Payment.PaymentStatus.FAILED
            payment.save()
            return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class PaynowUpdateView(APIView):
    permission_classes = [AllowAny]
    """
    The webhook (resulturl) view. Receives final status from Paynow.
    This now updates both the Payment and the associated Order.
    """
    def post(self, request, *args, **kwargs):
        raw_body = request.body.decode('utf-8')
        print("\n--- PAYNOW WEBHOOK RECEIVED ---")
        print("INCOMING RAW BODY:", raw_body)

        try:
            data = {item.split('=')[0]: unquote(item.split('=')[1]) for item in raw_body.split('&')}
        except IndexError:
            return Response({'error': 'Malformed webhook data'}, status=status.HTTP_400_BAD_REQUEST)

        received_hash = data.get('hash')
        reference = data.get('reference')

        try:
            # Use select_related to efficiently fetch the order at the same time
            payment = Payment.objects.select_related('order').get(reference=reference)
        except Payment.DoesNotExist:
            print(f"ERROR: Payment with reference {reference} not found!")
            return Response(status=status.HTTP_404_NOT_FOUND)

        # --- HASH VERIFICATION ---
        string_to_hash = ""
        for pair in raw_body.split('&'):
            key, value = pair.split('=', 1)
            if key.lower() != 'hash':
                string_to_hash += unquote(value)

        expected_hash = generate_hash(string_to_hash, settings.PAYNOW_INTEGRATION_KEY)

        if received_hash != expected_hash:
            print("!!! HASH MISMATCH. Webhook call is not authentic. !!!")
            payment.status = Payment.PaymentStatus.FAILED
            payment.save()
            return Response({'error': 'Invalid hash'}, status=status.HTTP_400_BAD_REQUEST)

        print(">>> HASH MATCH! Webhook is authentic. Updating status...")
        status_from_paynow = data.get('status', '').lower()

        # Get the related order from the payment object
        order = payment.order

        # --- UPDATE PAYMENT AND ORDER STATUS ---
        if status_from_paynow == 'paid':
            payment.status = Payment.PaymentStatus.PAID
            # Assuming your Order model has these fields:
            order.payment_status = True  # Use True for your BooleanField
            order.status = 'PR' 
        elif status_from_paynow == 'cancelled':
            payment.status = Payment.PaymentStatus.CANCELLEDorder.payment_status = False
            order.status = 'C'   
        else: # Covers 'failed', 'declined', etc.
            payment.status = Payment.PaymentStatus.FAILED
            order.payment_status = False # Still False if it failed

        payment.save()
        order.save()  # <-- CRITICAL: Save the updated order status!

        print(f"SUCCESS: Payment {reference} status: {payment.status}. Order {order.id} status: {order.status}")
        return Response(status=status.HTTP_200_OK)


class CheckPaymentStatusView(APIView):
    """An endpoint for the frontend to poll and check the final status of the payment."""
    def get(self, request, reference, *args, **kwargs):
        try:
            payment = Payment.objects.get(reference=reference)
            return Response({'status': payment.status}, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)







#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#----------------------------------------------------------------PayPal-------------------------------------------------------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Helper function to get a PayPal access token
def get_paypal_access_token():
    auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET)
    headers = {'Accept': 'application/json', 'Accept-Language': 'en_US'}
    data = {'grant_type': 'client_credentials'}
    url = f"{settings.PAYPAL_API_BASE}/v1/oauth2/token"
    
    try:
        response = requests.post(url, auth=auth, headers=headers, data=data)
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error getting PayPal token: {e}")
        return None

class PayPalCreateOrderView(APIView):
    def post(self, request, *args, **kwargs):
        order_id = request.data.get('order_id')
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        access_token = get_paypal_access_token()
        if not access_token:
            return Response({"error": "Could not authenticate with PayPal."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        url = f"{settings.PAYPAL_API_BASE}/v2/checkout/orders"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD", # Or your desired currency
                    "value": str(order.total_price)
                },
                "reference_id": str(order.order_number)
            }]
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return Response(response.json(), status=status.HTTP_201_CREATED)
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Failed to create PayPal order: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PayPalCaptureOrderView(APIView):
    def post(self, request, *args, **kwargs):
        paypal_order_id = request.data.get('paypal_order_id')
        user_order_id = request.data.get('user_order_id')

        access_token = get_paypal_access_token()
        if not access_token:
            return Response({"error": "Could not authenticate with PayPal."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        url = f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{paypal_order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }

        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=user_order_id, user=request.user)
                
                if order.payment_status:
                    return Response({"message": "Order already paid."}, status=status.HTTP_400_BAD_REQUEST)

                response = requests.post(url, headers=headers)
                response.raise_for_status()
                paypal_data = response.json()

                # CRITICAL: Verify the payment
                if paypal_data.get('status') == 'COMPLETED':
                    order.payment_status = True
                    order.status = 'PR'  # Set to Processing
                    order.save()
                    return Response({"message": "Payment successful!", "order_id": order.id}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Payment not completed by PayPal."}, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Failed to capture PayPal order: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)