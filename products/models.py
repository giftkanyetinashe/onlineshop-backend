from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.utils import timezone


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






class Product(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('U', 'Unisex'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.PROTECT)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    brand = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    




class ProductVariant(models.Model):
    SIZE_CHOICES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Extra Extra Large'),
    ]
    
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=3, choices=SIZE_CHOICES)
    sku = models.CharField(max_length=50, unique=True)
    stock = models.PositiveIntegerField(default=0)
    variant_image = models.ImageField(upload_to='variants/', null=True, blank=True)  # Added Image field for variants

    def __str__(self):
        return f"{self.product.name} - {self.color} - {self.size}"
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, related_name='variant_images', on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='products/')
    is_default = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True)  # Add the slug field

    def save(self, *args, **kwargs):
        # Automatically generate the slug based on the product's name or other criteria
        if not self.slug:  # If slug is empty, generate it
            if self.variant:  # Check if image is related to variant
                self.slug = slugify(f"{self.variant.product.name}-{self.variant.sku}-{self.variant.size}")
            else:
                self.slug = slugify(self.product.name)  # Slugify the product's name if no variant is provided
        super().save(*args, **kwargs)

    def __str__(self):
        if self.variant:
            return f"Image for {self.variant.product.name} Variant {self.variant.size} ({self.variant.color})"
        return f"Image for {self.product.name}"


