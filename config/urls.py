"""
URL configuration for smartsave project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from django.shortcuts import redirect


def home(request):
    return redirect('swagger-ui')

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/', include([
        path('auth/', include('apps.accounts.urls', namespace='accounts')),
        path('expenses/', include('apps.expenses.urls', namespace='expenses')),
        path('incomes/', include('apps.incomes.urls', namespace='incomes')),
        path('savings/', include('apps.savings.urls', namespace='savings')),
        path('budgets/', include('apps.budgets.urls', namespace='budgets')),
        path('analytics/', include('apps.analytics.urls', namespace='analytics')),
    ])),

    # مستندسازی
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
