from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'incomes'

router = DefaultRouter()
router.register('sources', views.IncomeSourceViewSet, basename='source')
router.register('', views.IncomeViewSet, basename='income')

urlpatterns = [
    path('', include(router.urls)),
]