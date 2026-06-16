import django_filters
from django_filters import rest_framework as filters
from .models import Income, IncomeSource


class IncomeFilter(filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')

    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')

    month = django_filters.NumberFilter(field_name='date', lookup_expr='month')
    year = django_filters.NumberFilter(field_name='date', lookup_expr='year')

    source = django_filters.ModelChoiceFilter(
        queryset=IncomeSource.objects.all()
    )
    source_slug = django_filters.CharFilter(
        field_name='source__slug',
        lookup_expr='exact'
    )

    class Meta:
        model = Income
        fields = [
            'source', 'source_slug', 'is_recurring',
            'date_from', 'date_to', 'amount_min', 'amount_max',
            'month', 'year',
        ]