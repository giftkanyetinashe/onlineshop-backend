# payments/models.py
from django.db import models
import uuid
# Make sure to import your Order model
# from orders.models import Order # <-- Adjust this import path as needed

class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    # Add a link to the Order
    # This is the most important change. It makes the payment belong to an order.
    # The 'on_delete=models.CASCADE' means if the order is deleted, the payment is too.
    # The 'related_name' lets you easily get payments from an order object (e.g., order.payments.all())
    order = models.ForeignKey(
        'orders.Order', # Use string reference to avoid circular imports
        on_delete=models.CASCADE, 
        related_name='payments',
        null=True, # Allow null temporarily if you have old payments without orders
        blank=True
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, default="Item Purchase")
    reference = models.CharField(max_length=100, unique=True)
    paynow_reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Order {self.order_id} - {self.status}"