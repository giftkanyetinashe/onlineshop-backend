from rest_framework import serializers
from .models import *
from django.urls import reverse  # This import was missing
from django.utils.text import slugify


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
        """Generate absolute URL for the category"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                reverse('category-detail', kwargs={'slug': obj.slug})
            )
        return None

    def get_breadcrumbs(self, obj):
        """Generate breadcrumb trail for the category"""
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
        """Prevent circular parent relationships"""
        if self.instance and value:
            if self.instance == value:
                raise serializers.ValidationError("A category cannot be its own parent.")
            if self._creates_circular_reference(self.instance, value):
                raise serializers.ValidationError("This would create a circular relationship.")
        return value

    def _creates_circular_reference(self, instance, new_parent):
        """Helper method to detect circular references"""
        current = new_parent
        while current:
            if current == instance:
                return True
            current = current.parent
        return False

    def create(self, validated_data):
        """Handle category creation with automatic slug generation"""
        if 'slug' not in validated_data or not validated_data['slug']:
            validated_data['slug'] = self.generate_unique_slug(
                validated_data['name'],
                validated_data.get('parent')
            )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Handle category updates including parent changes"""
        if 'name' in validated_data and 'slug' not in validated_data:
            validated_data['slug'] = self.generate_unique_slug(
                validated_data['name'],
                validated_data.get('parent', instance.parent)
            )
        return super().update(instance, validated_data)

    def get_total_product_count(self, obj):
        """Calculate total products including descendants"""

    def generate_unique_slug(self, name, parent=None):
        """Generate unique slug considering parent hierarchy"""
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



class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()  # Make sure you are not using 'source'

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_default', 'slug']  # Include 'slug' if needed


class ProductVariantSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = ProductVariant
        fields = ['id', 'product', 'color', 'size', 'sku', 'stock', 'variant_image']
        extra_kwargs = {
            'product': {'required': False}  # Allow product to be set later
        }

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    category = CategoryMiniSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    
    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {
            'category': {'required': True}
        }


