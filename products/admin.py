from django.contrib import admin
from .models import *
from django.utils.html import format_html
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin
from .forms import CategoryAdminForm
from django.utils.safestring import mark_safe


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'is_default']
    readonly_fields = ['thumbnail']

    def thumbnail(self, instance):
        if instance.image.name:
            # Return the HTML for the image thumbnail
            return mark_safe(f'<img src="{instance.image.url}" style="max-height: 100px; max-width: 100px;" />')
        return 'No image'
    thumbnail.allow_tags = True

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['color', 'size', 'sku', 'stock', 'variant_image']
    list_editable = ['color', 'size', 'sku', 'stock', 'variant_image']
@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    form = CategoryAdminForm
    list_display = (
        'tree_actions',
        'indented_title',
        'product_count',
        'is_featured',
        'display_order',
        'preview_image',
        'slug'
    )
    list_display_links = ('indented_title',)
    list_editable = ('is_featured', 'display_order')
    list_filter = ('is_featured', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'product_count', 'preview_image')
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'slug',
                'parent',
                'description',
                'display_order'
            )
        }),
        ('Images', {
            'fields': (
                'image',
                'preview_image'
            )
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': (
                'meta_title',
                'meta_description'
            )
        }),
        ('Flags', {
            'fields': (
                'is_featured',
            )
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': (
                'created_at',
                'updated_at',
                'product_count'
            )
        })
    )

    def preview_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return "-"
    preview_image.short_description = "Image Preview"

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "# Products"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('products')

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = obj._meta.model.objects.generate_unique_slug(obj.name, obj.parent)
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['parent'].queryset = Category.objects.exclude(
            pk=obj.pk
        ) if obj else Category.objects.all()
        return form

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'category', 
        'price', 
        'discount_price', 
        'gender', 
        'is_featured', 
        'is_active',
        'created_at'
    ]
    list_filter = ['category', 'gender', 'is_featured', 'is_active']
    search_fields = ['name', 'description', 'brand']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price')
        }),
        ('Details', {
            'fields': ('gender', 'brand', 'is_featured', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['name', '-created_at']

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'color', 'size', 'sku', 'stock']
    list_filter = ['product', 'size']
    search_fields = ['product__name', 'color', 'sku']
    list_editable = ['stock']
    raw_id_fields = ['product']
    ordering = ['product', 'size']
    inlines = [ProductImageInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')