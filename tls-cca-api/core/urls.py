from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import DashboardViewSet, GlobalSearchView

router = DefaultRouter()
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('search/', GlobalSearchView.as_view(), name='global-search'),
    *router.urls
]