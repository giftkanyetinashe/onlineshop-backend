from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings # Use settings for the User model


User = get_user_model()

class Category(MPTTModel):
    name = models.CharField(
        max_length=100,
        help_text="Name of the category (e.g., Clothing, Footwear)"
    )
    slug = models.SlugField(
        max_length=150,
        unique=True,
        help_text="URL-friendly version of the name (auto-generated if blank)"
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent category if this is a subcategory"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the category"
    )
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        help_text="Category display image"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured categories appear in special sections"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which categories appear (lower numbers first)"
    )
    meta_title = models.CharField(
        max_length=100,
        blank=True,
        help_text="SEO meta title (optional)"
    )
    meta_description = models.TextField(
        blank=True,
        help_text="SEO meta description (optional)"
    )
    created_at = models.DateTimeField(default=timezone.now, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class MPTTMeta:
        order_insertion_by = ['display_order', 'name']
        level_attr = 'mptt_level'  # Adds level tracking

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['parent', 'display_order']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_featured']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['slug', 'parent'],
                name='unique_slug_per_parent'
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug uniqueness when parent is specified
            if self.parent:
                self.slug = f"{self.parent.slug}-{self.slug}"
        super().save(*args, **kwargs)

    def get_full_path(self):
        """Returns the complete category hierarchy path"""
        names = []
        current = self
        while current is not None:
            names.insert(0, current.name)
            current = current.parent
        return ' > '.join(names)

    @property
    def level_name(self):
        """Returns indented name for display purposes"""
        return f"{'— ' * self.get_level()}{self.name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('category-detail', kwargs={'slug': self.slug})

    class Meta:
        verbose_name_plural = "Categories"
    
    @classmethod
    def annotate_product_counts(cls, queryset=None):
        from django.db.models import Count
        qs = queryset or cls.objects.all()
        return qs.annotate(product_count=Count('products', distinct=True))
    
    def get_all_products(self):
        """Get products from this category and all descendants"""
        from django.db.models import Q
        descendants = self.get_descendants(include_self=True)
        return Product.objects.filter(category__in=descendants)
    
    def get_breadcrumbs(self):
        ancestors = self.get_ancestors(include_self=True)
        return [
            {'name': cat.name, 'slug': cat.slug}
            for cat in ancestors
        ]







# --- NEW: A Tag Model for Powerful Filtering ---
# This allows you to create tags like "Vegan", "Cruelty-Free", "Sulfate-Free", etc.
# and filter products by them. This is a must-have feature.
class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



# --- UPGRADED: The World-Class Product Model ---
class Product(models.Model):
    # --- Existing Fields (Mostly Unchanged) ---
    name = models.CharField(max_length=200, help_text="The official product name.")
    slug = models.SlugField(unique=True, max_length=255)
    brand = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True, help_text="Controls product visibility on the site.")
    is_featured = models.BooleanField(default=False, help_text="Featured products appear on the homepage.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # --- Cosmetics-Specific Fields (The Upgrade) ---
    tagline = models.CharField(max_length=255, blank=True, help_text="A short, catchy phrase, e.g., 'The Ultimate Hydrating Serum'.")
    description = models.TextField(help_text="Detailed product description, benefits, and results.")
    
    ingredients = models.TextField(blank=True, help_text="Full list of ingredients, separated by commas.")
    how_to_use = models.TextField(blank=True, help_text="Step-by-step application instructions.")
    
    skin_types = models.CharField(max_length=100, blank=True, help_text="e.g., Oily, Dry, Combination, Sensitive, All")
    skin_concerns = models.CharField(max_length=255, blank=True, help_text="e.g., Acne, Fine Lines, Hyperpigmentation, Redness")

    # For makeup-specific products
    finish = models.CharField(max_length=50, blank=True, help_text="e.g., Matte, Dewy, Satin, Natural, Luminous")
    coverage = models.CharField(max_length=50, blank=True, help_text="e.g., Light, Medium, Full, Buildable")

    # --- NEW: Price moved to Variant ---
    # The base product no longer has a price. Each specific variant (size/shade) will have its own price.
    # We keep these fields on the product model for search/filtering convenience, but they should be considered display-only.
    display_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="The price of the default or most common variant, for display purposes.")
    
    # --- NEW: Relationship to Tags ---
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    # --- SEO Fields ---
    meta_title = models.CharField(max_length=255, blank=True, help_text="Optimized title for search engines.")
    meta_description = models.TextField(blank=True, help_text="Optimized description for search engines.")

    def __str__(self):
        return f"{self.brand} - {self.name}"

    def save(self, *args, **kwargs):
        # Update the display_price from the default variant whenever the product is saved
        super().save(*args, **kwargs) # Save first to ensure it has an ID
        default_variant = self.variants.order_by('id').first()
        if default_variant:
            self.display_price = default_variant.price
            # We call save again but prevent recursion
            super(Product, self).save(update_fields=['display_price'])





# --- UPGRADED: The World-Class ProductVariant Model ---
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    
    # --- NEW: Flexible Variant Attributes ---
    # Replaces the rigid 'size' and 'color' fields with more descriptive ones.
    size = models.CharField(max_length=50, blank=True, help_text="e.g., 30ml, 1.7oz, 5g")
    shade_name = models.CharField(max_length=100, blank=True, help_text="The descriptive name of the shade, e.g., 'Warm Ivory', 'Ruby Woo'")
    shade_hex_color = models.CharField(max_length=7, blank=True, help_text="The hex color code for the shade, e.g., '#F5DEB3'")

    # --- Price and Inventory Fields ---
    sku = models.CharField(max_length=100, unique=True, help_text="Unique Stock Keeping Unit.")
    upc = models.CharField(max_length=12, unique=True, null=True, blank=True, help_text="Universal Product Code.")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="The price for this specific variant.")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0, help_text="Current inventory level for this variant.")
    low_stock_threshold = models.PositiveIntegerField(default=10, help_text="Get a notification when stock falls to this level.")

    # --- Shipping Fields ---
    weight_grams = models.PositiveIntegerField(null=True, blank=True, help_text="Weight in grams for shipping calculations.")

    # --- Variant-Specific Image ---
    variant_image = models.ImageField(upload_to='variants/', null=True, blank=True, help_text="Optional: An image specific to this variant (e.g., a swatch).")

    def __str__(self):
        # Create a descriptive name based on the attributes it has
        variant_details = []
        if self.shade_name:
            variant_details.append(self.shade_name)
        if self.size:
            variant_details.append(self.size)
        
        if not variant_details:
             return f"{self.product.name} (Default)"
        
        return f"{self.product.name} ({', '.join(variant_details)})"
    





# --- NEW: Product Review Model ---
# Social proof is essential for a world-class store.
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    
    is_verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user') # User can only review a product once

    def __str__(self):
        return f'Review for {self.product.name} by {self.user.username}'



class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, related_name='variant_images', on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='products/')
    is_default = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True, max_length=255)  # Increased max_length

    def save(self, *args, **kwargs):
        # Automatically generate the slug based on the product's name or other criteria
        if not self.slug:  # If slug is empty, generate it
            if self.variant:  # Check if image is related to variant
                base_slug = slugify(f"{self.variant.product.name}-{self.variant.sku}")
                # Truncate if too long, but keep unique
                if len(base_slug) > 240:  # Leave room for uniqueness suffix
                    base_slug = base_slug[:240]
                self.slug = base_slug
            else:
                base_slug = slugify(self.product.name)
                # Truncate if too long, but keep unique
                if len(base_slug) > 240:  # Leave room for uniqueness suffix
                    base_slug = base_slug[:240]
                self.slug = base_slug
            
            # Ensure uniqueness by appending a counter if needed
            original_slug = self.slug
            counter = 1
            while ProductImage.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
                if counter > 100:  # Prevent infinite loop
                    self.slug = f"{original_slug[:200]}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        if self.variant:
            return f"Image for {self.variant.product.name} Variant {self.variant.size} ({self.variant.color})"
        return f"Image for {self.product.name}"


