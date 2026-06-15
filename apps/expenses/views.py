from datetime import date
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.permissions import IsOwner
from core.utils import calculate_savings_impact
from .models import Expense, Category, RecurringExpense
from .serializers import (
    CategorySerializer,
    ExpenseCreateSerializer,
    ExpenseUpdateSerializer,
    ExpenseSummarySerializer,
    SavingsImpactSerializer,
    RecurringExpenseSerializer,
    RecurringExpenseUpdateSerializer,
)
from .filters import ExpenseFilter


@extend_schema(tags=['Expenses'])
class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        # فقط دسته‌بندی‌های خود کاربر
        return Category.objects.filter(
            user=self.request.user
        ).annotate(
            expense_count=Count('expenses'),
            total_amount=Sum('expenses__amount')
        ).order_by('name')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # نمیشه دسته‌بندی پیش‌فرض رو حذف کرد
        if instance.is_default:
            return Response(
                {'error': 'Default categories cannot be deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


@extend_schema(tags=['Expenses'])
class ExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    filterset_class = ExpenseFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['description', 'category__name', 'category__slug']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ExpenseUpdateSerializer
        return ExpenseCreateSerializer

    def _auto_generate_recurring(self):
        """خودکار هزینه‌های تکرارشونده رو generate می‌کنه"""
        from datetime import date
        today = date.today()
        recurring_list = RecurringExpense.objects.filter(
            user=self.request.user,
            is_active=True
        )
        for recurring in recurring_list:
            should_generate = False
            if recurring.last_generated is None:
                should_generate = True
            elif recurring.frequency == RecurringExpense.Frequency.MONTHLY:
                should_generate = (
                        recurring.last_generated.month != today.month or
                        recurring.last_generated.year != today.year
                )
            elif recurring.frequency == RecurringExpense.Frequency.YEARLY:
                should_generate = recurring.last_generated.year != today.year
            elif recurring.frequency == RecurringExpense.Frequency.WEEKLY:
                should_generate = (today - recurring.last_generated).days >= 7
            elif recurring.frequency == RecurringExpense.Frequency.DAILY:
                should_generate = recurring.last_generated < today

            if recurring.end_date and today > recurring.end_date:
                recurring.is_active = False
                recurring.save()
                continue

            if should_generate:
                Expense.objects.create(
                    user=recurring.user,
                    category=recurring.category,
                    amount=recurring.amount,
                    description=f'[Recurring] {recurring.title}',
                    date=today,
                    is_recurring=True,
                )
                recurring.last_generated = today
                recurring.save()

    def get_queryset(self):
        # هر بار که لیست هزینه‌ها رو میگیره، recurring ها رو هم auto-generate کن
        self._auto_generate_recurring()
        return Expense.objects.filter(
            user=self.request.user
        ).select_related('category')

    @extend_schema(
        summary='List expenses',
        parameters=[
            OpenApiParameter('amount_min', OpenApiTypes.DECIMAL, description='Minimum amount'),
            OpenApiParameter('amount_max', OpenApiTypes.DECIMAL, description='Maximum amount'),
            OpenApiParameter('date_from', OpenApiTypes.DATE, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter('date_to', OpenApiTypes.DATE, description='End date (YYYY-MM-DD)'),
            OpenApiParameter('month', OpenApiTypes.INT, description='Month number (1-12)'),
            OpenApiParameter('year', OpenApiTypes.INT, description='Year (e.g. 2026)'),
            OpenApiParameter('category_slug', OpenApiTypes.STR, description='Category slug'),
            OpenApiParameter('is_recurring', OpenApiTypes.BOOL, description='Is recurring'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get expense summary',
        filters=False,
        responses=ExpenseSummarySerializer,
    )
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """خلاصه کلی هزینه‌ها"""
        queryset = self.filter_queryset(self.get_queryset())

        total = queryset.aggregate(
            total_amount=Sum('amount'),
            expense_count=Count('id'),
            average_amount=Avg('amount'),
        )

        by_category = Category.objects.filter(
            user=request.user
        ).annotate(
            expense_count=Count('expenses'),
            total_amount=Sum('expenses__amount')
        ).filter(expense_count__gt=0).order_by('-total_amount')

        return Response({
            'total_amount': total['total_amount'] or 0,
            'expense_count': total['expense_count'] or 0,
            'average_amount': total['average_amount'] or 0,
            'by_category': CategorySerializer(by_category, many=True).data,
        })

    @extend_schema(
        summary='Savings impact calculator',
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search term (e.g. cigarettes)',
                required=True,
            )
        ],
        filters=False,
        responses=SavingsImpactSerializer,
    )
    @action(detail=False, methods=['get'], url_path='savings-impact')
    def savings_impact(self, request):
        """ماشین حساب تأثیر پس‌انداز"""
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'error': 'Query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(category__slug__icontains=query)
        ).order_by('-date')

        total_spent = queryset.aggregate(total=Sum('amount'))['total'] or 0

        monthly_data = queryset.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(total=Sum('amount'))

        month_count = monthly_data.count() or 1
        monthly_average = total_spent / month_count

        return Response({
            'query': query,
            'total_spent': total_spent,
            'monthly_average': round(monthly_average, 2),
            'transaction_count': queryset.count(),
            'transactions': ExpenseCreateSerializer(queryset, many=True).data,
            'savings_impact': calculate_savings_impact(monthly_average),
        })


@extend_schema(tags=['Expenses'])
class RecurringExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'category__name']
    ordering_fields = ['amount', 'frequency', 'start_date', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return RecurringExpenseUpdateSerializer
        return RecurringExpenseSerializer

    def get_queryset(self):
        return RecurringExpense.objects.filter(
            user=self.request.user
        ).select_related('category')

    @extend_schema(
        summary='List recurring expenses',
        parameters=[
            OpenApiParameter('is_active', OpenApiTypes.BOOL, description='Filter by active status'),
            OpenApiParameter('frequency', OpenApiTypes.STR, description='Filter by frequency (daily/weekly/monthly/yearly)'),
        ]
    )
    def list(self, request, *args, **kwargs):
        is_active = request.query_params.get('is_active')
        frequency = request.query_params.get('frequency')

        queryset = self.filter_queryset(self.get_queryset())

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if frequency:
            queryset = queryset.filter(frequency=frequency)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Recurring expenses summary',
        filters=False,
    )
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """خلاصه هزینه‌های تکرارشونده"""
        queryset = self.get_queryset().filter(is_active=True)

        total_monthly = sum(r.monthly_cost for r in queryset)
        total_annual = total_monthly * 12

        by_frequency = {}
        for freq in RecurringExpense.Frequency:
            items = queryset.filter(frequency=freq.value)
            if items.exists():
                by_frequency[freq.value] = {
                    'count': items.count(),
                    'monthly_cost': sum(r.monthly_cost for r in items),
                }

        return Response({
            'total_monthly_cost': total_monthly,
            'total_annual_cost': total_annual,
            'active_count': queryset.count(),
            'by_frequency': by_frequency,
            'items': RecurringExpenseSerializer(queryset, many=True).data,
        })

    # @extend_schema(
    #     summary='Generate expenses from recurring',
    #     filters=False,
    # )
    # @action(detail=False, methods=['post'], url_path='generate')
    # def generate(self, request):
    #     """تولید هزینه‌های واقعی از هزینه‌های تکرارشونده"""
    #     today = date.today()
    #     generated_count = 0
    #     recurring_list = self.get_queryset().filter(is_active=True)
    #
    #     for recurring in recurring_list:
    #         should_generate = False
    #
    #         if recurring.last_generated is None:
    #             should_generate = True
    #         else:
    #             if recurring.frequency == RecurringExpense.Frequency.DAILY:
    #                 should_generate = recurring.last_generated < today
    #             elif recurring.frequency == RecurringExpense.Frequency.WEEKLY:
    #                 should_generate = (today - recurring.last_generated).days >= 7
    #             elif recurring.frequency == RecurringExpense.Frequency.MONTHLY:
    #                 should_generate = (
    #                     recurring.last_generated.month != today.month or
    #                     recurring.last_generated.year != today.year
    #                 )
    #             elif recurring.frequency == RecurringExpense.Frequency.YEARLY:
    #                 should_generate = recurring.last_generated.year != today.year
    #
    #         if recurring.end_date and today > recurring.end_date:
    #             recurring.is_active = False
    #             recurring.save()
    #             continue
    #
    #         if should_generate:
    #             Expense.objects.create(
    #                 user=recurring.user,
    #                 category=recurring.category,
    #                 amount=recurring.amount,
    #                 description=f'[Recurring] {recurring.title}',
    #                 date=today,
    #                 is_recurring=True,
    #             )
    #             recurring.last_generated = today
    #             recurring.save()
    #             generated_count += 1
    #
    #     return Response({
    #         'message': f'{generated_count} recurring expense(s) generated successfully',
    #         'generated_count': generated_count,
    #         'generated_date': today,
    #     })