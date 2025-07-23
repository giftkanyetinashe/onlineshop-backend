from rest_framework import serializers
from products.serializers import ProductVariantSerializer, ProductSerializer
from .models import Order, OrderItem, BannerContent
from products.models import *

# ------------------------------
# Order Item Serializer
# ------------------------------

class OrderItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    product = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'variant', 'product', 'quantity', 'price']

    def get_product(self, obj):
        if obj.variant and obj.variant.product:
            return ProductSerializer(obj.variant.product).data
        return None

# ------------------------------
# Order Serializer
# ------------------------------

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)


    # *** THIS IS THE KEY FIX ***
    # This creates a new field in the serializer output called 'order_id'
    # and tells it to get its value from the model's 'id' field.
    order_id = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['user', 'order_number', 'created_at', 'updated_at']

# ------------------------------
# Create Order Serializer
# ------------------------------

class CreateOrderSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField(),
        ),
        allow_empty=False
    )
    shipping_address = serializers.CharField()
    billing_address = serializers.CharField()
    payment_method = serializers.CharField()

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Items list cannot be empty.")

        for item in value:
            if 'variant_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError("Each item must have 'variant_id' and 'quantity'.")
            if not ProductVariant.objects.filter(id=item['variant_id']).exists():
                raise serializers.ValidationError(f"Variant with id {item['variant_id']} does not exist.")
            if item['quantity'] <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0.")

        return value








class ProductImageSerializer(serializers.ModelSerializer):
    """A simple serializer for the product's primary image."""
    class Meta:
        model = Product
        fields = ['image'] # Assuming your Product model has an 'image' field

class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for the product variant, including the product name and image."""
    # Source='variant.product' tells DRF to get the product object from the variant
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.URLField(source='product.image.url', read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'size', 'color', 'product_name', 'product_image']




# in serializers.py

class BannerContentSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    media_url_mobile = serializers.SerializerMethodField()

    class Meta:
        model = BannerContent
        fields = [
            'id', 'type', 'alt', 
            'media_file', 'media_file_mobile',  # <== Add these fields
            'media_url', 'media_url_mobile', 
            'overlay_text', 'cta_text', 'cta_link', 
            'duration', 'loop_video', 'order', 'is_active'
        ]

    def get_media_url(self, obj):
        request = self.context.get('request')
        if obj.media_file and request:
            return request.build_absolute_uri(obj.media_file.url)
        return None

    def get_media_url_mobile(self, obj):
        request = self.context.get('request')
        media_file = obj.media_file_mobile or obj.media_file
        if media_file and request:
            return request.build_absolute_uri(media_file.url)
        return None
