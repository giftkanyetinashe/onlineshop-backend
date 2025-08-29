from rest_framework import serializers
from .models import *
from django.urls import reverse  # This import was missing
from django.utils.text import slugify
from django.contrib.auth import get_user_model
User = get_user_model()
from django.db import transaction # Import the transaction module

from user.serializers import UserSerializer

# --- Recursive and Category Serializers (Unchanged) ---
# These are well-structured and don't need changes.

class RecursiveField(serializers.BaseSerializer):
    def to_representation(self, value):
        parent_serializer = self.parent.parent.__class__
        serializer = parent_serializer(value, context=self.context)
        return serializer.data

class CategorySerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    children = RecursiveField(many=True, read_only=True)
    parent = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    product_count = serializers.IntegerField(read_only=True)
    total_product_count = serializers.SerializerMethodField()
    breadcrumbs = serializers.SerializerMethodField()
    level = serializers.IntegerField(source='get_level', read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'url', 'description', 'image',
            'parent', 'children', 'is_featured', 'display_order',
            'product_count', 'total_product_count', 'meta_title', 'meta_description',
            'breadcrumbs', 'level', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'slug': {'required': False},
            'image': {'required': False}
        }

    def get_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                reverse('category-detail', kwargs={'slug': obj.slug})
            )
        return None

    def get_breadcrumbs(self, obj):
        breadcrumbs = []
        ancestors = obj.get_ancestors(include_self=True)
        for ancestor in ancestors:
            breadcrumbs.append({
                'name': ancestor.name,
                'slug': ancestor.slug,
                'url': self.get_url(ancestor)
            })
        return breadcrumbs

    def validate_parent(self, value):
        if self.instance and value:
            if self.instance == value:
                raise serializers.ValidationError("A category cannot be its own parent.")
            if self._creates_circular_reference(self.instance, value):
                raise serializers.ValidationError("This would create a circular relationship.")
        return value

    def _creates_circular_reference(self, instance, new_parent):
        current = new_parent
        while current:
            if current == instance:
                return True
            current = current.parent
        return False

    def create(self, validated_data):
        if 'slug' not in validated_data or not validated_data['slug']:
            validated_data['slug'] = self.generate_unique_slug(validated_data['name'], validated_data.get('parent'))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'name' in validated_data and 'slug' not in validated_data:
            validated_data['slug'] = self.generate_unique_slug(validated_data['name'], validated_data.get('parent', instance.parent))
        return super().update(instance, validated_data)

    def get_total_product_count(self, obj):
        return obj.get_all_products().count()

    def generate_unique_slug(self, name, parent=None):
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while True:
            if parent:
                exists = parent.children.filter(slug=slug).exists()
            else:
                exists = Category.objects.filter(parent__isnull=True, slug=slug).exists()
            if not exists:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug
    
class CategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'name']




# --- NEW: Serializer for Tags ---
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']

# --- NEW: Serializer for Reviews ---
class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True) # Display user info, but don't allow it to be changed

    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'title', 'comment', 'created_at', 'is_verified_purchase']
        read_only_fields = ['user', 'is_verified_purchase', 'created_at']


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()  # Make sure you are not using 'source'

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_default', 'slug']  # Include 'slug' if needed


#
# Variant serializer
#
class ProductVariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # useful for updates

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'upc', 'price', 'discount_price', 'stock',
            'low_stock_threshold', 'weight_grams', 'variant_image',
            'size', 'shade_name', 'shade_hex_color',
        ]
        read_only_fields = ('id',)


        
# --- NEW: A simple serializer just for creating variants ---
class ProductVariantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        # Include all fields that can be sent from the frontend
        fields = [
            'size', 'shade_name', 'shade_hex_color', 'sku', 'upc',
            'price', 'discount_price', 'stock', 'low_stock_threshold',
            'weight_grams', 'variant_image'
        ]





# --- UPGRADED: ProductSerializer ---
class ProductSerializer(serializers.ModelSerializer):
    # Nested serializers for related data
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    
    # Read-only representation of category and tags
    category = CategoryMiniSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    # --- THIS IS THE KEY CHANGE ---
    # We now define 'variants' twice. Once for reading (nested object)
    # and once for writing (accepting a list of variant data).
    variants = ProductVariantSerializer(many=True, read_only=True)
    variants_data = serializers.ListField(
        child=serializers.JSONField(), write_only=True, required=False
    )

    # Write-only fields for setting relationships on create/update
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), source='tags', write_only=True, many=True, required=False
    )
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'brand', 'tagline', 'description', 
            'ingredients', 'how_to_use', 'skin_types', 'skin_concerns',
            'finish', 'coverage', 'display_price',
            'is_active', 'is_featured',
            'meta_title', 'meta_description',
            'category', 'tags', 'images', 'variants', 'reviews', # Nested objects
            'category_id', 'tag_ids', 'variants_data',# Write-only fields
        ]
        read_only_fields = ['display_price']


    def create(self, validated_data):
        """
        Override the create method to handle nested variant creation.
        """
        # Pop the nested data from the validated data
        variants_data = validated_data.pop('variants_data', [])
        tags = validated_data.pop('tags', [])

        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # Create the main product instance
            product = Product.objects.create(**validated_data)
            product.tags.set(tags)

            # Loop through the variant data and create each variant
            for variant_data in variants_data:
                # Use our simple serializer for validation
                variant_serializer = ProductVariantCreateSerializer(data=variant_data)
                variant_serializer.is_valid(raise_exception=True)
                ProductVariant.objects.create(product=product, **variant_serializer.validated_data)
        
        # The save() method on the Product model will automatically update display_price
        product.save()
        return product