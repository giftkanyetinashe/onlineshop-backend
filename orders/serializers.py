from rest_framework import serializers
from products.serializers import ProductSerializer, ProductVariantSerializer
from .models import Order, OrderItem, BannerContent, PromoCode
from user.serializers import UserSerializer

# ------------------------------
# Order Item Serializer
# ------------------------------

class OrderItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    product = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'variant', 'product', 'product_name', 'product_image', 'quantity', 'price']

    def get_product(self, obj):
        if obj.variant and obj.variant.product:
            try:
                return ProductSerializer(obj.variant.product).data
            except Exception:
                return None
        return None

    def get_product_name(self, obj):
        if obj.variant and obj.variant.product:
            return obj.variant.product.name
        return 'Product Name Unavailable'

    def get_product_image(self, obj):
        if obj.variant and obj.variant.product:
            product = obj.variant.product
            if hasattr(product, 'images') and product.images.exists():
                first_image = product.images.first()
                if first_image and first_image.image:
                    return first_image.image.url
        return None

# ------------------------------
# Order Serializer
# ------------------------------

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    order_id = serializers.IntegerField(source='id', read_only=True)
    user = UserSerializer(read_only=True)

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
    promo_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Items list cannot be empty.")

        for item in value:
            if 'variant_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError("Each item must have 'variant_id' and 'quantity'.")
            from products.models import ProductVariant
            if not ProductVariant.objects.filter(id=item['variant_id']).exists():
                raise serializers.ValidationError(f"Variant with id {item['variant_id']} does not exist.")
            if item['quantity'] <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0.")

        return value

    def create(self, validated_data):
        # The actual creation logic is handled in the view's perform_create method
        # This method just returns the validated data for the view to process
        return validated_data

# ------------------------------
# Banner Content Serializer
# ------------------------------

class BannerContentSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    media_url_mobile = serializers.SerializerMethodField()

    class Meta:
        model = BannerContent
        fields = [
            'id', 'type', 'alt', 
            'media_file', 'media_file_mobile',
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

# ------------------------------
# Promo Code Validation Serializer
# ------------------------------

class PromoCodeValidationSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    
    def validate_code(self, value):
        try:
            promo = PromoCode.objects.get(code=value.upper())
        except PromoCode.DoesNotExist:
            raise serializers.ValidationError("Invalid promo code.")
        
        if not promo.is_active:
            raise serializers.ValidationError("This promo code is no longer active.")
        
        from django.utils import timezone
        if promo.valid_from > timezone.now():
            raise serializers.ValidationError("This promo code is not yet valid.")
        
        if promo.valid_to and promo.valid_to < timezone.now():
            raise serializers.ValidationError("This promo code has expired.")
        
        return value
