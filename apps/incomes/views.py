from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from core.permissions import IsOwner
from .models import Income, IncomeSource
from .serializers import (
    IncomeCreateSerializer,
    IncomeUpdateSerializer,
    IncomeSourceSerializer,
    IncomeSourceUpdateSerializer,
    IncomeSummarySerializer,
    MonthlyIncomeReportSerializer,
)
from .filters import IncomeFilter


@extend_schema(tags=['Incomes'])
class IncomeSourceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return IncomeSourceUpdateSerializer
        return IncomeSourceSerializer

    def get_queryset(self):
        return IncomeSource.objects.filter(
            user=self.request.user
        ).annotate(
            income_count=Count('incomes'),
            total_amount=Sum('incomes__amount')
        ).order_by('name')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # نمیشه منبع درآمدی پیش‌فرض رو حذف کرد
        if instance.is_default:
            return Response(
                {'error': 'Default income sources cannot be deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

@extend_schema(tags=['Incomes'])
class IncomeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    filterset_class = IncomeFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['description', 'source__name', 'source__slug']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']

    @extend_schema(
        summary='List incomes',
        parameters=[
            OpenApiParameter('amount_min', OpenApiTypes.DECIMAL, description='Minimum amount'),
            OpenApiParameter('amount_max', OpenApiTypes.DECIMAL, description='Maximum amount'),
            OpenApiParameter('date_from', OpenApiTypes.DATE, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter('date_to', OpenApiTypes.DATE, description='End date (YYYY-MM-DD)'),
            OpenApiParameter('month', OpenApiTypes.INT, description='Month number (1-12)'),
            OpenApiParameter('year', OpenApiTypes.INT, description='Year (e.g. 2026)'),
            OpenApiParameter('source_slug', OpenApiTypes.STR, description='Source slug'),
            OpenApiParameter('is_recurring', OpenApiTypes.BOOL, description='Is recurring'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return IncomeUpdateSerializer
        return IncomeCreateSerializer

    def get_queryset(self):
        return Income.objects.filter(
            user=self.request.user
        ).select_related('source')

    @extend_schema(
        summary='Get income summary',
        responses=IncomeSummarySerializer,
    )
    @extend_schema(
        summary='Get income summary',
        filters=False,
        responses=IncomeSummarySerializer,
    )
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """خلاصه کلی درآمدها"""
        queryset = self.filter_queryset(self.get_queryset())

        total = queryset.aggregate(
            total_amount=Sum('amount'),
            income_count=Count('id'),
            average_amount=Avg('amount'),
        )

        by_source = IncomeSource.objects.filter(
            user=request.user
        ).annotate(
            income_count=Count('incomes'),
            total_amount=Sum('incomes__amount')
        ).filter(income_count__gt=0).order_by('-total_amount')

        return Response({
            'total_amount': total['total_amount'] or 0,
            'income_count': total['income_count'] or 0,
            'average_amount': total['average_amount'] or 0,
            'by_source': IncomeSourceSerializer(by_source, many=True).data,
        })

    @extend_schema(
        summary='Monthly income report',
        parameters=[
            OpenApiParameter(
                name='year',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Year (e.g. 2026)',
                required=False,
            )
        ],
        filters=False,
    )
    @action(detail=False, methods=['get'], url_path='monthly-report')
    def monthly_report(self, request):
        """گزارش درآمد ماهانه"""
        queryset = self.get_queryset()

        year = request.query_params.get('year')
        if year:
            queryset = queryset.filter(date__year=year)

        monthly_data = queryset.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total_amount=Sum('amount'),
            income_count=Count('id'),
        ).order_by('month')

        return Response(list(monthly_data))

    @extend_schema(
        summary='Compare income vs expenses',
        parameters=[
            OpenApiParameter(
                name='year',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Year (e.g. 2026)',
                required=False,
            )
        ],
    )
    @extend_schema(
        summary='Compare income vs expenses',
        parameters=[
            OpenApiParameter(
                name='year',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Year (e.g. 2026)',
                required=False,
            )
        ],
        filters=False,
    )
    @action(detail=False, methods=['get'], url_path='vs-expenses')
    def vs_expenses(self, request):
        """مقایسه درآمد و هزینه ماهانه"""
        from apps.expenses.models import Expense

        year = request.query_params.get('year')

        income_qs = self.get_queryset()
        expense_qs = Expense.objects.filter(user=request.user)

        if year:
            income_qs = income_qs.filter(date__year=year)
            expense_qs = expense_qs.filter(date__year=year)

        monthly_income = {
            item['month']: item['total']
            for item in income_qs.annotate(
                month=TruncMonth('date')
            ).values('month').annotate(total=Sum('amount'))
        }

        monthly_expense = {
            item['month']: item['total']
            for item in expense_qs.annotate(
                month=TruncMonth('date')
            ).values('month').annotate(total=Sum('amount'))
        }

        all_months = sorted(set(list(monthly_income.keys()) + list(monthly_expense.keys())))

        result = []
        for month in all_months:
            income = monthly_income.get(month, 0)
            expense = monthly_expense.get(month, 0)
            result.append({
                'month': month,
                'income': income,
                'expense': expense,
                'balance': income - expense,
                'savings_rate': round((income - expense) / income * 100, 2) if income else 0,
            })

        return Response(result)