from django.contrib import admin
from .models import *
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from mptt.admin import DraggableMPTTAdmin
from .forms import CategoryAdminForm

# --- Category Admin ---
@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    form = CategoryAdminForm
    list_display = (
        'tree_actions', 'indented_title', 'product_count', 'is_featured',
        'display_order', 'preview_image', 'slug'
    )
    list_display_links = ('indented_title',)
    list_editable = ('is_featured', 'display_order')
    list_filter = ('is_featured', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'product_count', 'preview_image')

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description', 'display_order')
        }),
        ('Images', {
            'fields': ('image', 'preview_image')
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': ('meta_title', 'meta_description')
        }),
        ('Flags', {
            'fields': ('is_featured',)
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at', 'product_count')
        }),
    )

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "-"
    preview_image.short_description = "Image Preview"

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "# Products"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('products')

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = obj._meta.model.objects.generate_unique_slug(obj.name, obj.parent)
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['parent'].queryset = Category.objects.exclude(pk=obj.pk) if obj else Category.objects.all()
        return form

# --- Product Inlines ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'is_default', 'thumbnail']
    readonly_fields = ['thumbnail']

    def thumbnail(self, instance):
        if instance.image:
            return mark_safe(f'<img src="{instance.image.url}" style="max-height: 100px; max-width: 100px;" />')
        return 'No image'
    thumbnail.short_description = "Preview"

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = [
        'size', 'shade_name', 'shade_hex_color',
        'sku', 'upc', 'price', 'discount_price',
        'stock', 'low_stock_threshold', 'weight_grams',
        'variant_image', 'variant_preview'
    ]
    readonly_fields = ['variant_preview']

    def variant_preview(self, obj):
        if obj.variant_image:
            return mark_safe(f'<img src="{obj.variant_image.url}" style="max-height: 80px;" />')
        return "No image"
    variant_preview.short_description = "Preview"

# --- Product Admin ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'category', 'display_price', 'is_featured', 'is_active']
    list_filter = ['category', 'brand', 'tags', 'is_featured', 'is_active']
    search_fields = ['name', 'tagline', 'description', 'brand']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'display_price']
    inlines = [ProductVariantInline, ProductImageInline]
    filter_horizontal = ('tags',)
    ordering = ['name', '-created_at']

    fieldsets = (
        ('Core Information', {
            'fields': ('name', 'slug', 'brand', 'category', 'tagline')
        }),
        ('Marketing & Content', {
            'fields': ('description', 'ingredients', 'how_to_use')
        }),
        ('Cosmetics Details (Suitability)', {
            'fields': ('skin_types', 'skin_concerns', 'finish', 'coverage')
        }),
        ('Pricing & Visibility', {
            'fields': ('display_price', 'is_active', 'is_featured', 'tags')
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': ('meta_title', 'meta_description')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

# --- Tag Admin ---
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

# --- Review Admin ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'title', 'created_at', 'is_verified_purchase')
    list_filter = ('rating', 'created_at', 'is_verified_purchase')
    search_fields = ('title', 'comment', 'user__username', 'product__name')
    readonly_fields = ('user', 'product', 'created_at')

    def has_add_permission(self, request):
        return False  # Reviews should only be created from the frontend
