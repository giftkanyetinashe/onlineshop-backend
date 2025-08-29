# reports/urls.py

from django.urls import path
from .views import ReportsDashboardView

urlpatterns = [
    path('dashboard/', ReportsDashboardView.as_view(), name='reports-dashboard'),
]