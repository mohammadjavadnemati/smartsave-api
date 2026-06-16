import django_filters
from django_filters import rest_framework as filters
from .models import Expense, Category


class ExpenseFilter(filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')

    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')

    month = django_filters.NumberFilter(field_name='date', lookup_expr='month')
    year = django_filters.NumberFilter(field_name='date', lookup_expr='year')

    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all()
    )
    category_slug = django_filters.CharFilter(
        field_name='category__slug',
        lookup_expr='exact'
    )

    class Meta:
        model = Expense
        fields = [
            'category', 'category_slug', 'is_recurring',
            'date_from', 'date_to', 'amount_min', 'amount_max',
            'month', 'year',
        ]