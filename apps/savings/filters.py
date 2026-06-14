import django_filters
from django_filters import rest_framework as filters
from .models import SavingsGoal


class SavingsGoalFilter(filters.FilterSet):
    min_target = django_filters.NumberFilter(
        field_name='target_amount', lookup_expr='gte'
    )
    max_target = django_filters.NumberFilter(
        field_name='target_amount', lookup_expr='lte'
    )
    min_progress = django_filters.NumberFilter(
        field_name='current_amount', lookup_expr='gte'
    )
    deadline_before = django_filters.DateFilter(
        field_name='deadline', lookup_expr='lte'
    )
    deadline_after = django_filters.DateFilter(
        field_name='deadline', lookup_expr='gte'
    )

    class Meta:
        model = SavingsGoal
        fields = ['status', 'min_target', 'max_target', 'deadline_before', 'deadline_after']