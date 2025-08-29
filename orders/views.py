# orders/views.py

from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.parsers import MultiPartParser, FormParser
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import random
import string

from .models import BannerContent, Order, OrderItem, PromoCode
from .serializers import (
    BannerContentSerializer, OrderSerializer, CreateOrderSerializer,
    PromoCodeValidationSerializer
)
from products.models import ProductVariant
from user.models import User # Use your actual user model path

# =================================================================
# Banner Content Views (Cleaned Up)
# =================================================================

class BannerContentListCreate(generics.ListCreateAPIView):
    queryset = BannerContent.objects.filter(is_active=True).order_by('order')
    serializer_class = BannerContentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

class BannerContentDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = BannerContent.objects.all()
    serializer_class = BannerContentSerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

# =================================================================
# Order Views (Consolidated into a World-Class ViewSet)
# =================================================================

class OrderViewSet(viewsets.ModelViewSet):
    """
    A unified ViewSet for viewing and creating orders.
    - Admins can see all orders.
    - Regular users can only see and manage their own orders.
    - Provides powerful filtering for the admin dashboard.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Define fields available for filtering
    filterset_fields = {
        'status': ['exact', 'in'],
        'payment_status': ['exact'],
        'created_at': ['gte', 'lte', 'exact', 'range'] # Allows for date range filtering
    }
    search_fields = ['order_number', 'user__username', 'user__email', 'shipping_address']
    ordering_fields = ['created_at', 'total_price']

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            # Admins can see all orders, highly optimized query
            return Order.objects.all().select_related('user').prefetch_related(
                'items__variant__product__images'
            ).order_by('-created_at')
        
        # Regular users only see their own orders
        return Order.objects.filter(user=user).select_related('user').prefetch_related(
            'items__variant__product__images'
        ).order_by('-created_at')

    def perform_create(self, serializer):
        # The 'create' method is now the 'perform_create' hook in a ViewSet
        with transaction.atomic():
            validated_data = serializer.validated_data
            
            # --- Secure Promo Code Validation ---
            promo_code_str = validated_data.get('promo_code')
            promo_code_obj = None
            if promo_code_str:
                try:
                    # Re-validate the promo code right before creating the order
                    promo_code_obj = PromoCode.objects.get(code=promo_code_str.upper(), is_active=True)
                    # You can add more checks here if needed (e.g., expiry, usage limit)
                except PromoCode.DoesNotExist:
                    raise ValidationError("The provided promo code is invalid or has expired.")

            # --- Secure Price Calculation (Backend-Only) ---
            total_price = Decimal('0.0')
            items_data = validated_data['items']
            for item_data in items_data:
                variant = ProductVariant.objects.select_for_update().get(id=item_data['variant_id'])
                if variant.stock < item_data['quantity']:
                    raise ValidationError(f'Not enough stock for "{variant.product.name}". Only {variant.stock} left.')
                
                item_price = variant.discount_price or variant.price
                total_price += item_price * item_data['quantity']

            # --- Calculate Discount ---
            discount_amount = Decimal('0.0')
            if promo_code_obj:
                if promo_code_obj.discount_type == 'PERCENT':
                    discount_amount = total_price * (promo_code_obj.value / Decimal('100.0'))
                elif promo_code_obj.discount_type == 'FIXED':
                    discount_amount = promo_code_obj.value
            
            final_price = total_price - discount_amount

            order = serializer.save(
                user=self.request.user,
                order_number='ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)),
                total_price=final_price,
                promo_code=promo_code_obj,
                discount_amount=discount_amount
            )
            
            # Create OrderItem instances and update stock
            for item_data in items_data:
                variant = ProductVariant.objects.get(id=item_data['variant_id'])
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=item_data['quantity'],
                    price=variant.discount_price or variant.price
                )
                variant.stock -= item_data['quantity']
                variant.save()

# --- NEW: MyOrderListView for frontend user profiles ---
# This is a cleaner, dedicated endpoint separate from the main ViewSet.
class MyOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

# =================================================================
# Other Views (Dashboard, Promo Validation)
# =================================================================
class DashboardSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        try:
            # Get date range from query params
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            
            # Base queryset
            orders = Order.objects.all()
            
            # Apply date filtering if provided
            if from_date:
                orders = orders.filter(created_at__gte=from_date)
            if to_date:
                orders = orders.filter(created_at__lte=to_date)
            
            # Calculate summary metrics
            total_orders = orders.count()
            total_revenue = orders.aggregate(
                total=Coalesce(Sum('total_price'), Decimal('0.0'), output_field=DecimalField())
            )['total']
            
            # Order status breakdown
            status_breakdown = orders.values('status').annotate(
                count=Count('id'),
                revenue=Coalesce(Sum('total_price'), Decimal('0.0'), output_field=DecimalField())
            )
            
            # Payment status breakdown
            payment_breakdown = orders.values('payment_status').annotate(
                count=Count('id'),
                revenue=Coalesce(Sum('total_price'), Decimal('0.0'), output_field=DecimalField())
            )
            
            # Recent orders (last 5)
            recent_orders = orders.order_by('-created_at')[:5]
            recent_orders_data = OrderSerializer(recent_orders, many=True).data
            
            # Top selling products
            top_products = OrderItem.objects.filter(
                order__in=orders
            ).values(
                'variant__product__name'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Coalesce(
                    Sum('price', output_field=DecimalField()), 
                    Decimal('0.0'), 
                    output_field=DecimalField()
                )
            ).order_by('-total_quantity')[:5]
            
            # Daily sales for the last 7 days
            end_date = timezone.now().date()
            start_date = end_date - timezone.timedelta(days=6)
            
            daily_sales = orders.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            ).values('created_at__date').annotate(
                orders_count=Count('id'),
                daily_revenue=Coalesce(
                    Sum('total_price'), 
                    Decimal('0.0'), 
                    output_field=DecimalField()
                )
            ).order_by('created_at__date')
            
            # Calculate additional metrics for frontend compatibility
            today = timezone.now().date()
            sales_today = orders.filter(created_at__date=today).aggregate(
                total=Coalesce(Sum('total_price'), Decimal('0.0'), output_field=DecimalField())
            )['total']
            
            # This month sales
            sales_this_month = orders.filter(
                created_at__year=today.year,
                created_at__month=today.month
            ).aggregate(
                total=Coalesce(Sum('total_price'), Decimal('0.0'), output_field=DecimalField())
            )['total']
            
            # New customers this week
            new_customers_this_week = User.objects.filter(
                date_joined__gte=today - timezone.timedelta(days=7)
            ).count()
            
            # Order status counts
            orders_pending = orders.filter(status='Pending').count()
            orders_shipped = orders.filter(status='Shipped').count()
            orders_delivered_today = orders.filter(
                status='Delivered',
                updated_at__date=today
            ).count()
            
            # Out of stock and low stock items
            out_of_stock_count = ProductVariant.objects.filter(stock=0).count()
            low_stock_items = ProductVariant.objects.filter(
                stock__gt=0,
                stock__lt=10
            ).select_related('product').values(
                'id',
                'product__name',
                'stock'
            )[:5]
            
            # Format low stock items
            formatted_low_stock = [
                {
                    'id': item['id'],
                    'name': item['product__name'],
                    'stock': item['stock']
                }
                for item in low_stock_items
            ]
            
            # Format top selling products for frontend
            formatted_top_products = [
                {
                    'variant__product__name': item['variant__product__name'],
                    'total_sold': item['total_quantity']
                }
                for item in top_products
            ]
            
            # Format daily sales for frontend
            formatted_daily_sales = [
                {
                    'date': sale['created_at__date'].strftime('%Y-%m-%d'),
                    'sales': float(sale['daily_revenue'])
                }
                for sale in daily_sales
            ]
            
            # Format recent orders for frontend
            formatted_recent_orders = [
                {
                    'id': order.id,
                    'customer_name': f"{order.user.first_name} {order.user.last_name}".strip() or order.user.username,
                    'total': float(order.total_price),
                    'status': order.status
                }
                for order in recent_orders
            ]
            
            response_data = {
                'sales_today': float(sales_today),
                'sales_this_month': float(sales_this_month),
                'avg_order_value': float(total_revenue / total_orders) if total_orders > 0 else 0.0,
                'new_customers_this_week': new_customers_this_week,
                'orders_pending': orders_pending,
                'orders_shipped': orders_shipped,
                'orders_delivered_today': orders_delivered_today,
                'out_of_stock_count': out_of_stock_count,
                'low_stock_items': formatted_low_stock,
                'top_selling_products': formatted_top_products,
                'sales_over_time': formatted_daily_sales,
                'recent_orders': formatted_recent_orders,
                'summary': {
                    'total_orders': total_orders,
                    'total_revenue': float(total_revenue),
                    'average_order_value': float(total_revenue / total_orders) if total_orders > 0 else 0.0
                },
                'status_breakdown': list(status_breakdown),
                'payment_breakdown': list(payment_breakdown),
                'daily_sales': list(daily_sales)
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ValidatePromoCodeView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        try:
            serializer = PromoCodeValidationSerializer(data=request.data)
            if serializer.is_valid():
                code = serializer.validated_data['code'].upper()
                
                try:
                    promo_code = PromoCode.objects.get(
                        code=code,
                        is_active=True
                    )
                    
                    # Check if promo code has expired
                    if promo_code.expiry_date and promo_code.expiry_date < timezone.now().date():
                        return Response(
                            {'valid': False, 'error': 'Promo code has expired'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    return Response({
                        'valid': True,
                        'code': promo_code.code,
                        'discount_type': promo_code.discount_type,
                        'value': float(promo_code.value)
                    }, status=status.HTTP_200_OK)
                    
                except PromoCode.DoesNotExist:
                    return Response(
                        {'valid': False, 'error': 'Invalid promo code'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response(
                {'valid': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            return Response(
                {'valid': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
