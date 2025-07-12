from django.urls import path
from .views import UserCreate, UserDetail, CustomTokenObtainPairView

urlpatterns = [
    path('register/', UserCreate.as_view(), name='user-register'),
    path('me/', UserDetail.as_view(), name='user-detail'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
]