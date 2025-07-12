from django import forms
from django.core.exceptions import ValidationError
from .models import Category

class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'

    def clean_parent(self):
        """
        Validate parent without using get_descendants() on unsaved instance
        """
        parent = self.cleaned_data.get('parent')
        instance = self.instance
        
        if instance and instance.pk and parent:
            # Only check for circular relationships if instance exists in DB
            if instance.pk == parent.pk:
                raise ValidationError("A category cannot be its own parent")
            
            # Get all ancestor PKs to check for circular relationships
            ancestor_pks = parent.get_ancestors(include_self=True).values_list('pk', flat=True)
            if instance.pk in ancestor_pks:
                raise ValidationError(
                    "This would create a circular relationship. "
                    "Selected parent is already a child of this category."
                )
        
        return parent