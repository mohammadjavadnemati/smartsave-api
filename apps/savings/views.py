from decimal import Decimal
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
from core.utils import calculate_months_to_goal
from .models import SavingsGoal, SavingsDeposit
from .serializers import (
    SavingsGoalSerializer,
    SavingsGoalUpdateSerializer,
    SavingsDepositSerializer,
    SavingsDepositUpdateSerializer,
    GoalProgressSerializer,
)
from .filters import SavingsGoalFilter


@extend_schema(tags=['Savings'])
class SavingsGoalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    filterset_class = SavingsGoalFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'target_amount', 'current_amount', 'deadline']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return SavingsGoalUpdateSerializer
        return SavingsGoalSerializer

    def get_queryset(self):
        return SavingsGoal.objects.filter(
            user=self.request.user
        ).prefetch_related('deposits')

    @extend_schema(
        summary='List savings goals',
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status (active/completed/cancelled)'),
            OpenApiParameter('min_target', OpenApiTypes.DECIMAL, description='Minimum target amount'),
            OpenApiParameter('max_target', OpenApiTypes.DECIMAL, description='Maximum target amount'),
            OpenApiParameter('deadline_before', OpenApiTypes.DATE, description='Deadline before date'),
            OpenApiParameter('deadline_after', OpenApiTypes.DATE, description='Deadline after date'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Overall savings progress',
        filters=False,
        responses=GoalProgressSerializer,
    )
    @action(detail=False, methods=['get'], url_path='progress')
    def progress(self, request):
        """Overall savings goals progress"""
        goals = SavingsGoal.objects.filter(user=request.user)

        stats = goals.aggregate(
            total_goals=Count('id'),
            total_saved=Sum('current_amount'),
            total_target=Sum('target_amount'),
        )

        active_count = goals.filter(status=SavingsGoal.Status.ACTIVE).count()
        completed_count = goals.filter(status=SavingsGoal.Status.COMPLETED).count()

        total_saved = stats['total_saved'] or Decimal('0')
        total_target = stats['total_target'] or Decimal('1')
        overall_progress = round(float(total_saved / total_target * 100), 2)

        return Response({
            'total_goals': stats['total_goals'] or 0,
            'active_goals': active_count,
            'completed_goals': completed_count,
            'total_saved': total_saved,
            'total_target': stats['total_target'] or Decimal('0'),
            'overall_progress': min(overall_progress, 100),
        })

    @extend_schema(
        summary='Predict months to reach goal',
        filters=False,
        parameters=[
            OpenApiParameter(
                'monthly_saving',
                OpenApiTypes.DECIMAL,
                description='Expected monthly saving amount',
                required=True,
            )
        ],
    )
    @action(detail=True, methods=['get'], url_path='predict')
    def predict(self, request, pk=None):
        """
        Estimate time to reach the goal
        Example: With saving $250 per month, you will reach the goal in 40 months
        """
        goal = self.get_object()
        monthly_saving = request.query_params.get('monthly_saving')

        if not monthly_saving:
            return Response(
                {'error': 'monthly_saving parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            monthly_saving = Decimal(monthly_saving)
        except Exception:
            return Response(
                {'error': 'Invalid monthly_saving value'},
                status=status.HTTP_400_BAD_REQUEST
            )

        months = calculate_months_to_goal(
            goal.current_amount,
            goal.target_amount,
            monthly_saving
        )

        if months is None:
            return Response(
                {'error': 'Monthly saving must be greater than 0'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if months == 0:
            message = 'You have already reached your goal!'
        else:
            years = months // 12
            remaining_months = months % 12
            if years > 0:
                message = f'You will reach your goal in approximately {years} year(s) and {remaining_months} month(s)'
            else:
                message = f'You will reach your goal in approximately {months} month(s)'

        return Response({
            'goal': goal.title,
            'target_amount': goal.target_amount,
            'current_amount': goal.current_amount,
            'remaining_amount': goal.remaining_amount,
            'monthly_saving': monthly_saving,
            'months_to_goal': months,
            'message': message,
        })


@extend_schema(tags=['Savings'])
class SavingsDepositViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['note']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return SavingsDepositUpdateSerializer
        return SavingsDepositSerializer

    def get_queryset(self):
        return SavingsDeposit.objects.filter(
            goal__user=self.request.user
        ).select_related('goal')

    def perform_create(self, serializer):
        deposit = serializer.save()
        goal = deposit.goal
        goal.current_amount += deposit.amount
        if goal.current_amount >= goal.target_amount:
            goal.status = SavingsGoal.Status.COMPLETED
        goal.save()

    def perform_destroy(self, instance):
        goal = instance.goal
        goal.current_amount = max(
            goal.current_amount - instance.amount,
            Decimal('0.00')
        )
        if goal.status == SavingsGoal.Status.COMPLETED:
            if goal.current_amount < goal.target_amount:
                goal.status = SavingsGoal.Status.ACTIVE
        goal.save()
        instance.delete()