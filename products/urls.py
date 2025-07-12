from django.urls import path
from django.views.generic.base import RedirectView
from .views import *

urlpatterns = [
    
    path('products/', ProductList.as_view(), name='product-list'),
    path('products/featured/', FeaturedProducts.as_view(), name='featured-products'),
    path('products/<slug:slug>/', ProductDetail.as_view(), name='product-detail'),
    path('products/<slug:product_slug>/variants/', ProductVariantListView.as_view(), name='product-variants-list'),
    path('products/<slug:product_slug>/variants/<int:pk>/', ProductVariantDetailView.as_view(), name='product-variant-detail'),
    # ... other URLs ...
    path('products/<slug:product_slug>/images/', ProductImageView.as_view(), name='product-images-list'),
    path('products/<slug:product_slug>/images/<int:pk>/', ProductImageDetailView.as_view(), name='product-image-detail'),

    path('categories', RedirectView.as_view(url='categories/', permanent=True)),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<slug:slug>/products/', CategoryProductsView.as_view(), name='category-products'),
    
]
