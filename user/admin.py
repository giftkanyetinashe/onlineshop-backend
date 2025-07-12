from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User

class UserAdmin(BaseUserAdmin):
    list_display = [
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'is_staff', 
        'is_active',
        'avatar_tag'
    ]
    list_filter = ['is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['last_login', 'date_joined', 'avatar_tag']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {
            'fields': (
                'first_name', 
                'last_name', 
                'email', 
                'avatar', 
                'avatar_tag',
                'phone'
            )
        }),
        ('Address', {
            'fields': ('address', 'city', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    filter_horizontal = ('groups', 'user_permissions',)

    def avatar_tag(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.avatar.url
            )
        return 'No avatar'
    avatar_tag.short_description = 'Avatar'

admin.site.register(User, UserAdmin)