from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'savings'

router = DefaultRouter()
router.register('goals', views.SavingsGoalViewSet, basename='goal')
router.register('deposits', views.SavingsDepositViewSet, basename='deposit')

urlpatterns = [
    path('', include(router.urls)),
]