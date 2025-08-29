# user/urls.py

from django.urls import path, include
from .views import UserCreate, UserDetail, CustomTokenObtainPairView, UserAdminViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', UserAdminViewSet, basename='user-admin')

urlpatterns = [
    # --- THIS IS THE FIX ---
    # The paths now correctly point to the views defined in your views.py
    path('register/', UserCreate.as_view(), name='user-register'),
    path('me/', UserDetail.as_view(), name='user-detail'), 
    path('login/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    # --- END OF FIX ---
    path('admin/', include(router.urls)),
]