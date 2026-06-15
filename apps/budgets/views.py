from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.permissions import IsOwner
from .models import Budget
from .serializers import (
    BudgetSerializer,
    BudgetUpdateSerializer,
    BudgetAlertSerializer,
    BudgetSummarySerializer,
)
from .filters import BudgetFilter


@extend_schema(tags=['Budgets'])
class BudgetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    filterset_class = BudgetFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['category__name', 'category__slug']
    ordering_fields = ['amount', 'year', 'month', 'created_at']
    ordering = ['-year', '-month']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return BudgetUpdateSerializer
        return BudgetSerializer

    def get_queryset(self):
        return Budget.objects.filter(
            user=self.request.user
        ).select_related('category')

    @extend_schema(
        summary='List budgets',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, description='Filter by year'),
            OpenApiParameter('month', OpenApiTypes.INT, description='Filter by month (1-12)'),
            OpenApiParameter('period', OpenApiTypes.STR, description='Filter by period (monthly/weekly/yearly)'),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, description='Filter by active status'),
            OpenApiParameter('category_slug', OpenApiTypes.STR, description='Filter by category slug'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get budget alerts',
        filters=False,
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, description='Year (default: current year)'),
            OpenApiParameter('month', OpenApiTypes.INT, description='Month (default: current month)'),
            OpenApiParameter('category_slug', OpenApiTypes.STR, description='Filter by category slug'),
        ],
        responses=BudgetAlertSerializer(many=True),
    )
    @action(detail=False, methods=['get'], url_path='alerts')
    def alerts(self, request):
        """
        هشدارهای بودجه:
        - ۸۰٪ بودجه خوراکی مصرف شده
        - بودجه حمل و نقل رد شده
        """
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        category_slug = request.query_params.get('category_slug')

        budgets = Budget.objects.filter(
            user=request.user,
            year=year,
            month=month,
            is_active=True,
        ).select_related('category')

        # فیلتر بر اساس category_slug اگه داده شده بود
        if category_slug:
            budgets = budgets.filter(category__slug=category_slug)

        alerts = []
        for budget in budgets:
            alert_level = budget.alert_level

            # همه بودجه‌ها رو نشون بده نه فقط هشدارها
            if alert_level == 'exceeded':
                message = (
                    f'You have exceeded your {budget.category.name} budget '
                    f'by ${abs(budget.remaining_amount):.2f}'
                )
            elif alert_level == 'warning':
                message = (
                    f'{budget.usage_percentage:.0f}% of your '
                    f'{budget.category.name} budget has been used'
                )
            else:
                message = (
                    f'Your {budget.category.name} budget is on track '
                    f'({budget.usage_percentage:.0f}% used)'
                )

            alerts.append({
                'budget_id': budget.id,
                'category_name': budget.category.name,
                'category_slug': budget.category.slug,
                'alert_level': alert_level,
                'usage_percentage': budget.usage_percentage,
                'spent_amount': budget.spent_amount,
                'budget_amount': budget.amount,
                'remaining_amount': budget.remaining_amount,
                'message': message,
            })

        # اول exceeded بعد warning بعد none
        alerts.sort(key=lambda x: (
            0 if x['alert_level'] == 'exceeded'
            else 1 if x['alert_level'] == 'warning'
            else 2
        ))

        return Response(alerts)

    @extend_schema(
        summary='Get budget summary',
        filters=False,
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, description='Year (default: current year)'),
            OpenApiParameter('month', OpenApiTypes.INT, description='Month (default: current month)'),
        ],
        responses=BudgetSummarySerializer,
    )
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """خلاصه بودجه‌بندی ماهانه"""
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))

        budgets = Budget.objects.filter(
            user=request.user,
            year=year,
            month=month,
            is_active=True,
        ).select_related('category')

        total_budget = Decimal('0')
        total_spent = Decimal('0')
        on_track = 0
        warning = 0
        exceeded = 0
        alerts = []

        for budget in budgets:
            total_budget += budget.amount
            total_spent += budget.spent_amount
            alert_level = budget.alert_level

            if alert_level == 'none':
                on_track += 1
            elif alert_level == 'warning':
                warning += 1
            else:
                exceeded += 1

            if alert_level != 'none':
                if alert_level == 'exceeded':
                    message = (
                        f'You have exceeded your {budget.category.name} budget '
                        f'by ${abs(budget.remaining_amount):.2f}'
                    )
                else:
                    message = (
                        f'{budget.usage_percentage:.0f}% of your '
                        f'{budget.category.name} budget has been used'
                    )
                alerts.append({
                    'budget_id': budget.id,
                    'category_name': budget.category.name,
                    'alert_level': alert_level,
                    'usage_percentage': budget.usage_percentage,
                    'spent_amount': budget.spent_amount,
                    'budget_amount': budget.amount,
                    'remaining_amount': budget.remaining_amount,
                    'message': message,
                })

        total_remaining = total_budget - total_spent
        overall_usage = (
            round(float(total_spent / total_budget * 100), 2)
            if total_budget > 0 else 0
        )

        return Response({
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_remaining': total_remaining,
            'overall_usage_percentage': overall_usage,
            'budgets_on_track': on_track,
            'budgets_warning': warning,
            'budgets_exceeded': exceeded,
            'alerts': alerts,
        })