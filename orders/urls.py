# orders/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BannerContentListCreate, BannerContentDetail, OrderViewSet, MyOrderListView,
    DashboardSummaryView, ValidatePromoCodeView
)

# A router provides all necessary URLs for a ViewSet automatically
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('banner/', BannerContentListCreate.as_view(), name='banner-list-create'),
    path('banner/<int:pk>/', BannerContentDetail.as_view(), name='banner-detail'),
    
    # The router handles list, create, retrieve, update, delete for orders
    path('', include(router.urls)),
    
    # Dedicated URLs for specific, non-standard actions
    path('my-orders/', MyOrderListView.as_view(), name='my-order-list'),
    path('admin/dashboard-summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('validate-promo/', ValidatePromoCodeView.as_view(), name='validate-promo'),
]