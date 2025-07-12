from django.db import models
from django.contrib.auth import get_user_model
from products.models import ProductVariant

User = get_user_model()

class Order(models.Model):
    STATUS_CHOICES = [
        ('P', 'Pending'),
        ('PR', 'Processing'),
        ('S', 'Shipped'),
        ('D', 'Delivered'),
        ('C', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, related_name='orders', on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='P')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipping_address = models.TextField()
    billing_address = models.TextField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    payment_status = models.BooleanField(default=False)
    tracking_number = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.order_number

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.name} in order {self.order.order_number}"

class BannerContent(models.Model):
    TYPE_CHOICES = [
        ('video', 'Video'),
        ('image', 'Image'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    src = models.URLField(max_length=500, blank=True, null=True)
    media_file = models.FileField(upload_to='banner_media/' , blank=True, null=True)
    alt = models.CharField(max_length=255)
    duration = models.PositiveIntegerField(default=5000)  # duration in milliseconds
    overlayText = models.CharField(max_length=255)
    ctaText = models.CharField(max_length=100)
    ctaLink = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.type} - {self.alt}"
