from django.contrib import admin
from .models import *

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['variant', 'quantity', 'price']
    fields = ['variant', 'quantity', 'price', 'item_total']
    
    def item_total(self, obj):
        return obj.quantity * obj.price
    item_total.short_description = 'Total'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 
        'user', 
        'status', 
        'total_price', 
        'payment_status', 
        'created_at'
    ]
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'total_price']
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Payment', {
            'fields': ('total_price', 'payment_method', 'payment_status')
        }),
        ('Addresses', {
            'fields': ('shipping_address', 'billing_address'),
            'classes': ('collapse',)
        }),
        ('Shipping', {
            'fields': ('tracking_number',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_shipped', 'mark_as_delivered']

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='S')
    mark_as_shipped.short_description = "Mark selected orders as shipped"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='D')
    mark_as_delivered.short_description = "Mark selected orders as delivered"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    


@admin.register(BannerContent)
class BannerContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'alt', 'overlayText', 'ctaText', 'duration')
    list_filter = ('type',)
    search_fields = ('alt', 'overlayText', 'ctaText')
    ordering = ('id',)