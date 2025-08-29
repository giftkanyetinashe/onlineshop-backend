# user/views.py

from django.db.models import Count, Sum, DecimalField 
from rest_framework import generics, permissions, viewsets

from django.db.models.functions import Coalesce
from .models import User
from .serializers import UserSerializer, CustomTokenObtainPairSerializer, UserAdminSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser

# --- Your existing UserCreate and UserDetail views are fine ---
class UserCreate(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class UserDetail(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    # --- THIS IS THE FIX ---
    # Tell the view to accept both JSON and file upload data
    parser_classes = [MultiPartParser, FormParser]
    
    def get_object(self):
        return self.request.user
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
# --- UPGRADED UserAdminViewSet ---
class UserAdminViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing and editing users in the admin panel.
    Only accessible by staff members.
    """
    serializer_class = UserAdminSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        # Use annotations to efficiently calculate order data at the database level
        return User.objects.annotate(
            order_count=Count('orders', distinct=True),
            # --- THIS IS THE FIX ---
            # We explicitly tell Django that the output of this operation is a DecimalField.
            total_spent=Coalesce(Sum('orders__total_price'), 0.0, output_field=DecimalField())
        ).order_by('-date_joined')