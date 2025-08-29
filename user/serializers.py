from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'address', 'city', 'country', 'postal_code',
            'avatar', 'password' ,'is_staff'
        ]
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        # Your create method is correct.
        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['is_staff'] = user.is_staff  # Add is_staff claim to token
        return token



class UserAdminSerializer(serializers.ModelSerializer):
    """
    Provides detailed user information for the admin dashboard,
    including calculated fields for order history.
    """
    order_count = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'is_staff', 'is_active', 'date_joined',
            'order_count', 'total_spent'
        ]