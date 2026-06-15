from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('trends/', views.MonthlyTrendView.as_view(), name='trends'),
    path('categories/', views.CategoryExpenseView.as_view(), name='categories'),
    path('health/', views.FinancialHealthView.as_view(), name='health'),
    path('insights/', views.SmartInsightsView.as_view(), name='insights'),
]