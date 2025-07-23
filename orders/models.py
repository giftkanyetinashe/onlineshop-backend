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
    TYPE_CHOICES = [('video', 'Video'), ('image', 'Image')]

    # Core Fields
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='image')
    alt = models.CharField(max_length=255, help_text="Important for SEO and accessibility.")
    
    # Media Fields (World-Class Upgrade)
    media_file = models.FileField(upload_to='banner_media/', help_text="Desktop version (landscape recommended).")
    media_file_mobile = models.FileField(upload_to='banner_media/mobile/', blank=True, null=True, help_text="Optional: Mobile version (portrait recommended). If empty, desktop version is used.")

    # Overlay Content
    overlay_text = models.CharField(max_length=255)
    cta_text = models.CharField(max_length=100)
    cta_link = models.CharField(max_length=255, help_text="e.g., /products/revitalizing-serum")

    # Control Fields (World-Class Upgrade)
    duration = models.PositiveIntegerField(default=7000, help_text="For images: duration in milliseconds (e.g., 7000 = 7 seconds).")
    loop_video = models.BooleanField(default=False, help_text="For videos: check if the video should loop instead of advancing.")
    order = models.PositiveIntegerField(default=0, help_text="Order in which banner appears (0 first, 1 second, etc.).")
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this banner from the site without deleting it.")
    
    class Meta:
        ordering = ['order'] # Ensure banners are ordered correctly by default

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.alt} (Order: {self.order}) - [{status}]"