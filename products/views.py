from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView 
from rest_framework.response import Response
# Create your views here.
from mptt.templatetags.mptt_tags import cache_tree_children
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.urls import reverse
from rest_framework import generics, filters, permissions, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import *




class CategoryListView(generics.ListCreateAPIView):
    """
    Unified view that handles both flat list and tree structure formats.
    Accessible via: /api/products/categories/?format=flat or ?tree
    """
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Filters categories based on parent slug and ensures it's ready for serialization
        """
        queryset = Category.objects.filter(parent__isnull=True)  # Only top-level categories

        # Filtering by parent slug if provided
        parent_slug = self.request.query_params.get('parent')
        if parent_slug:
            queryset = Category.objects.filter(parent__slug=parent_slug)

        return queryset.prefetch_related(
            'children__children__children'  # Allows deep prefetch for tree format
        ).order_by('display_order', 'name')

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests, delegating to the correct response format (flat or tree)
        """
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        Handles the GET request and determines whether to return flat or tree response.
        """
        format_type = 'tree' if 'tree' in request.query_params else 'flat'  # Check for 'tree' in query params
        if format_type == 'tree':
            return self.get_tree_response()  # Call tree format response
        return self.get_flat_response()  # Default to flat format response

    def get_flat_response(self):
        """
        Returns categories in a flat list format
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'categories': serializer.data,
            'meta': {
                'format': 'flat',
                'count': queryset.count()
            }
        })

    def get_tree_response(self):
        """
        Returns categories in a hierarchical tree format
        """
        try:
            root_nodes = Category.objects.filter(parent__isnull=True)  # Only top-level categories
            data = self._recursive_serialize(root_nodes)  # Serialize in tree format
            return Response({
                'categories': data,
                'meta': {
                    'format': 'tree',
                    'count': len(data)
                }
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _recursive_serialize(self, nodes):
        """
        Serializes categories and their children recursively for the tree structure
        """
        serializer = self.get_serializer(nodes, many=True)
        data = serializer.data
        for i, node in enumerate(nodes):
            # Fetch the children of the current category
            children = node.get_children()
            if children:
                # If the category has children, serialize them recursively
                data[i]['children'] = self._recursive_serialize(children)
        return data

    def perform_create(self, serializer):
        """
        Creates a new category, calculating the display order based on the parent
        """
        parent = serializer.validated_data.get('parent')
        if parent:
            last_order = Category.objects.filter(
                parent=parent
            ).order_by('-display_order').values_list('display_order', flat=True).first()
            serializer.validated_data['display_order'] = (last_order or 0) + 1
        serializer.save()


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

class CategoryProductsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return category.products.all()
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Enhanced detail view with better query optimization
    """
    queryset = Category.objects.all().select_related('parent').prefetch_related('children')
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    def perform_update(self, serializer):
        # Regenerate slug if name changed
        if 'name' in serializer.validated_data:
            name = serializer.validated_data['name']
            parent = serializer.validated_data.get('parent', serializer.instance.parent)
            serializer.validated_data['slug'] = self._generate_unique_slug(name, parent)
        serializer.save()

    def _generate_unique_slug(self, name, parent=None):
        """Reuse the same slug generation logic"""
        serializer = CategorySerializer()
        return serializer.generate_unique_slug(name, parent)

class CategoryProductsView(generics.ListAPIView):
    """
    Product listing view with pagination support
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        category = get_object_or_404(
            Category.objects.select_related('parent'),
            slug=self.kwargs['slug']
        )
        return category.products.all().select_related('category')



class ProductList(generics.ListCreateAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'gender', 'is_featured']
    search_fields = ['name', 'description', 'brand']
    ordering_fields = ['price', 'created_at', 'updated_at']
    permission_classes = [IsAuthenticatedOrReadOnly]

class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    permission_classes = [IsAuthenticatedOrReadOnly]

class FeaturedProducts(generics.ListAPIView):
    queryset = Product.objects.filter(is_featured=True, is_active=True)
    serializer_class = ProductSerializer


class ProductVariantListView(ListCreateAPIView):  # Now supports GET + POST
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return ProductVariant.objects.filter(product__slug=self.kwargs['product_slug'])

    def perform_create(self, serializer):
        product = Product.objects.get(slug=self.kwargs['product_slug'])
        serializer.save(product=product)  # Auto-link variant to product

class ProductImageView(generics.ListCreateAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return ProductImage.objects.filter(product__slug=self.kwargs['product_slug'])

    def perform_create(self, serializer):
        product = Product.objects.get(slug=self.kwargs['product_slug'])
        serializer.save(product=product)

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProductVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return ProductVariant.objects.filter(product__slug=self.kwargs['product_slug'])