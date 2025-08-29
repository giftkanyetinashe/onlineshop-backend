# reports/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDay
from django.utils.dateparse import parse_date
from datetime import timedelta
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product
from user.models import User

class ReportsDashboardView(APIView):
    """
    A world-class API view to generate comprehensive e-commerce reports.
    It aggregates data for KPIs, charts, and tables based on a date range.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        # --- 1. Date Filtering ---
        end_date = request.query_params.get('end_date', timezone.now().strftime('%Y-%m-%d'))
        start_date = request.query_params.get('start_date', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))

        # Ensure we have valid date objects
        start_date_obj = parse_date(start_date)
        end_date_obj = parse_date(end_date) + timedelta(days=1) # Include the whole end day

        # Base querysets filtered by the selected date range
        orders_in_range = Order.objects.filter(created_at__range=[start_date_obj, end_date_obj], payment_status=True)
        users_in_range = User.objects.filter(date_joined__range=[start_date_obj, end_date_obj])

        # --- 2. Calculate Key Performance Indicators (KPIs) ---
        kpis = orders_in_range.aggregate(
            total_revenue=Sum('total_price'),
            total_sales=Count('id'),
            average_order_value=Avg('total_price')
        )
        kpis['new_customers'] = users_in_range.count()
        # Handle cases with no sales
        for key in ['total_revenue', 'total_sales', 'average_order_value']:
            if kpis[key] is None:
                kpis[key] = 0

        # --- 3. Sales Over Time Data (for Line Chart) ---
        sales_over_time = (
            orders_in_range
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(daily_revenue=Sum('total_price'))
            .order_by('day')
        )
        sales_over_time_data = [{'date': item['day'].strftime('%Y-%m-%d'), 'revenue': item['daily_revenue']} for item in sales_over_time]

        # --- 4. Top Selling Products Data (for Bar Chart & Table) ---
        top_products = (
            OrderItem.objects.filter(order__in=orders_in_range)
            .values('variant__product__name', 'variant__product__brand')
            .annotate(
                units_sold=Sum('quantity'),
                product_revenue=Sum(F('quantity') * F('price'))
            )
            .order_by('-product_revenue')[:10] # Top 10 products
        )
        top_products_data = list(top_products)

        # --- 5. Sales by Category Data (for Pie Chart) ---
        sales_by_category = (
            OrderItem.objects.filter(order__in=orders_in_range)
            .values('variant__product__category__name')
            .annotate(category_revenue=Sum(F('quantity') * F('price')))
            .order_by('-category_revenue')
        )
        sales_by_category_data = [{'name': item['variant__product__category__name'], 'value': item['category_revenue']} for item in sales_by_category]
        
        # --- 6. Construct the final response payload ---
        response_data = {
            'kpis': kpis,
            'sales_over_time': sales_over_time_data,
            'top_products': top_products_data,
            'sales_by_category': sales_by_category_data,
        }

        return Response(response_data, status=status.HTTP_200_OK)