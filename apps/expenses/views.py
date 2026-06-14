from django.db.models import Sum, Count, Avg, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from core.permissions import IsOwner
from core.utils import calculate_savings_impact
from .models import Expense, Category
from .serializers import (
    ExpenseCreateSerializer,
    ExpenseUpdateSerializer,
    CategorySerializer,
    ExpenseSummarySerializer,
    SavingsImpactSerializer,
)
from .filters import ExpenseFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend



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

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ExpenseUpdateSerializer
        return ExpenseCreateSerializer

    def get_queryset(self):
        return Expense.objects.filter(
            user=self.request.user
        ).select_related('category')

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

        # هزینه بر اساس دسته‌بندی
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
            'by_category': CategorySerializer(
                by_category, many=True
            ).data,
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
        """
        ماشین حساب تأثیر پس‌انداز
        کاربر سرچ می‌کنه مثلاً 'سیگار' و میبینه:
        - تمام خریدهای مرتبط با تاریخ
        - جمع کل هزینه‌ها
        - اگه این هزینه‌ها رو نداشت الان چقدر پول بیشتر داشت
        """
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'error': 'Query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # سرچ در توضیحات و نام دسته‌بندی
        queryset = self.get_queryset().filter(
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(category__slug__icontains=query)
        ).order_by('-date')

        total_spent = queryset.aggregate(
            total=Sum('amount')
        )['total'] or 0

        # محاسبه میانگین ماهانه
        from django.db.models.functions import TruncMonth
        monthly_data = queryset.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        )
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