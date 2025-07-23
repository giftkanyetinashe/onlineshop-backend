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
    list_display = (
        'alt', 'type', 'order', 'is_active', 'duration', 'loop_video', 'preview_media'
    )
    list_filter = ('type', 'is_active', 'loop_video')
    search_fields = ('alt', 'overlay_text', 'cta_text', 'cta_link')
    list_editable = ('order', 'is_active')
    ordering = ('order',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('type', 'alt', 'overlay_text', 'cta_text', 'cta_link')
        }),
        ('Media Files', {
            'fields': ('media_file', 'media_file_mobile'),
            'description': 'Desktop and optional mobile version of the media.'
        }),
        ('Display Settings', {
            'fields': ('duration', 'loop_video', 'order', 'is_active'),
            'description': 'Control how the banner behaves and appears.'
        }),
    )

    def preview_media(self, obj):
        if obj.media_file:
            if obj.type == 'image':
                return f'<img src="{obj.media_file.url}" width="100" />'
            else:
                return f'<video width="100" controls><source src="{obj.media_file.url}" type="video/mp4"></video>'
        return "-"
    preview_media.short_description = "Preview"
    preview_media.allow_tags = True  # This is deprecated in Django 2+, use format_html if needed

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()