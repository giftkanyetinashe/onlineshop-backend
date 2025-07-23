from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminUserOrReadOnly

from rest_framework.parsers import MultiPartParser, FormParser
from .models import BannerContent, Order, OrderItem
from .serializers import (
    BannerContentSerializer,
    OrderSerializer,
    CreateOrderSerializer
)
from products.models import ProductVariant
import random
import string
from rest_framework.views import APIView
from django.db import transaction
from rest_framework import filters # Add this import

# ------------------------------
# Banner Content Views
# ------------------------------

class BannerContentListCreate(generics.ListCreateAPIView):
    # World-Class Upgrade: Only show active banners on the public site
    queryset = BannerContent.objects.filter(is_active=True).order_by('order') 
    serializer_class = BannerContentSerializer
    # Allow anyone to view, but only staff to create/edit
    permission_classes = [IsAdminUserOrReadOnly] 
    parser_classes = [MultiPartParser, FormParser]
    # No filter_backends needed if default ordering is set in queryset

# ... The Detail view remains mostly the same, but should also use IsAdminUserOrReadOnly


class BannerContentDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = BannerContent.objects.all()
    serializer_class = BannerContentSerializer
    permission_classes = [permissions.IsAdminUser] # Use IsAdminUser for detail view
    parser_classes = [MultiPartParser, FormParser]

    # --- THIS IS THE FIX ---
    # Override the partial_update method to correctly handle file uploads
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Handle boolean fields from form data which come as strings
        for field in ['is_active', 'loop_video']:
            if field in request.data:
                request.data[field] = request.data[field].lower() in ['true', '1']
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)

# ------------------------------
# Order Views
# ------------------------------

class OrderListCreate(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        # Use CreateOrderSerializer for POST requests (creating an order)
        if self.request.method == 'POST':
            return CreateOrderSerializer
        # Use OrderSerializer for GET requests (listing orders)
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all().order_by('-created_at')
        return Order.objects.filter(user=user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # *** USE A DATABASE TRANSACTION FOR SAFETY ***
        # This ensures that if any step fails (e.g., stock update),
        # the entire operation is rolled back, preventing partial/corrupt orders.
        with transaction.atomic():
            # Generate a unique order number
            order_number = 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            
            # Create the initial Order object
            order = Order.objects.create(
                user=request.user,
                order_number=order_number,
                shipping_address=serializer.validated_data['shipping_address'],
                billing_address=serializer.validated_data['billing_address'],
                payment_method=serializer.validated_data['payment_method'],
                total_price=0,  # Initialize to 0, will calculate next
                payment_status=False, # Default to not paid
                status='P' # Default to Pending
            )

            total_price = 0
            items_data = serializer.validated_data['items']

            for item_data in items_data:
                variant_id = item_data.get('variant_id')
                quantity = item_data.get('quantity')

                # Use select_for_update to lock the variant row to prevent race conditions
                try:
                    variant = ProductVariant.objects.select_for_update().get(id=variant_id)
                except ProductVariant.DoesNotExist:
                    # The transaction will automatically roll back
                    return Response(
                        {'error': f'Variant with ID {variant_id} does not exist'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if variant.stock < quantity:
                    # The transaction will automatically roll back
                    return Response(
                        {'error': f'Not enough stock for "{variant.product.name}". Only {variant.stock} left.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Use the price from the database, not the frontend, for security
                item_price = variant.product.discount_price or variant.product.price
                total_price += item_price * quantity

                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=quantity,
                    price=item_price
                )

                # Update stock
                variant.stock -= quantity
                variant.save()

            # Now save the final calculated price to the order
            order.total_price = total_price
            order.save()

        # Serialize the final order object using the MODIFIED OrderSerializer
        final_order_data = OrderSerializer(order).data
        return Response(final_order_data, status=status.HTTP_201_CREATED)

class OrderDetail(generics.RetrieveUpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all().prefetch_related('items__variant__product')
        return Order.objects.filter(user=user).prefetch_related('items__variant__product')
    

class CreateOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        items_data = serializer.validated_data['items']
        shipping_address = serializer.validated_data['shipping_address']
        billing_address = serializer.validated_data['billing_address']
        payment_method = serializer.validated_data['payment_method']

        with transaction.atomic():
            # Generate a unique order number
            order_number = f"ORD-{random.randint(100000, 999999)}"
            while Order.objects.filter(order_number=order_number).exists():
                order_number = f"ORD-{random.randint(100000, 999999)}"

            # Calculate total price
            total_price = 0
            order_items = []

            for item in items_data:
                variant_id = item.get('variant_id')
                quantity = item.get('quantity')

                try:
                    variant = ProductVariant.objects.select_related('product').get(id=variant_id)
                except ProductVariant.DoesNotExist:
                    return Response({"error": f"Variant with ID {variant_id} not found."}, status=status.HTTP_404_NOT_FOUND)

                price = variant.price * quantity
                total_price += price
                order_items.append((variant, quantity, price))

            # Create Order
            order = Order.objects.create(
                user=request.user,
                order_number=order_number,
                shipping_address=shipping_address,
                billing_address=billing_address,
                payment_method=payment_method,
                total_price=total_price,
                payment_status=False  # Default; update this later after payment confirmation
            )

            # Create Order Items
            for variant, quantity, price in order_items:
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=quantity,
                    price=price
                )

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)





class OrderHistoryView(generics.ListAPIView):
    """
    API view to retrieve a list of orders for the currently authenticated user.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated] # Ensures user is logged in

    def get_queryset(self):
        """
        This view should return a list of all the orders
        for the currently authenticated user.
        """
        user = self.request.user
        # Order by most recent first
        return Order.objects.filter(user=user).order_by('-created_at')