from django.urls import path
from .views import *
urlpatterns = [
    path('orders/', OrderListCreate.as_view(), name='order-list-create'),
    path('my-orders/', OrderHistoryView.as_view(), name='my-orders'),
    path('orders/<int:pk>/', OrderDetail.as_view(), name='order-detail'),
    path('banner/', BannerContentListCreate.as_view(), name='banner-list-create'),
    path('banner/<int:pk>/', BannerContentDetail.as_view(), name='banner-detail'),
]
