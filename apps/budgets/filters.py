import django_filters
from django_filters import rest_framework as filters
from .models import Budget


class BudgetFilter(filters.FilterSet):
    year = django_filters.NumberFilter(field_name='year')
    month = django_filters.NumberFilter(field_name='month')
    category_slug = django_filters.CharFilter(
        field_name='category__slug',
        lookup_expr='exact'
    )

    class Meta:
        model = Budget
        fields = ['year', 'month', 'period', 'is_active', 'category_slug']