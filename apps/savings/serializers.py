from rest_framework import serializers
from .models import SavingsGoal, SavingsDeposit
from core.utils import calculate_months_to_goal
from django.db.models import Sum
from django.db.models.functions import TruncMonth

class SavingsDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsDeposit
        fields = ('id', 'goal', 'amount', 'note', 'date', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_goal(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError('Invalid goal')
        if value.status != SavingsGoal.Status.ACTIVE:
            raise serializers.ValidationError(
                'Cannot deposit to a completed or cancelled goal'
            )
        return value


class SavingsDepositUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsDeposit
        fields = ('id', 'goal', 'amount', 'note', 'date', 'created_at')
        read_only_fields = ('id', 'created_at')
        extra_kwargs = {
            'goal': {'required': False},
            'amount': {'required': False},
            'note': {'required': False},
            'date': {'required': False},
        }

    def validate_goal(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError('Invalid goal')
        return value


class SavingsGoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.FloatField(read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    is_completed = serializers.BooleanField(read_only=True)
    months_to_goal = serializers.SerializerMethodField()
    recent_deposits = serializers.SerializerMethodField()

    class Meta:
        model = SavingsGoal
        fields = (
            'id', 'title', 'description', 'target_amount', 'current_amount',
            'remaining_amount', 'progress_percentage', 'is_completed',
            'deadline', 'status', 'months_to_goal', 'recent_deposits',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'current_amount', 'created_at', 'updated_at')

    def get_months_to_goal(self, obj):
        """
        Calculate the number of months required to reach the goal
        based on the average monthly deposits
        """


        monthly_avg = obj.deposits.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).aggregate(avg=Sum('total'))

        deposit_months = obj.deposits.annotate(
            month=TruncMonth('date')
        ).values('month').distinct().count()

        if not deposit_months:
            return None

        total_deposited = monthly_avg['avg'] or 0
        monthly_average = total_deposited / deposit_months

        return calculate_months_to_goal(
            obj.current_amount,
            obj.target_amount,
            monthly_average
        )

    def get_recent_deposits(self, obj):
        """Last 5 deposits"""
        deposits = obj.deposits.order_by('-date')[:5]
        return SavingsDepositSerializer(deposits, many=True).data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SavingsGoalUpdateSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.FloatField(read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = SavingsGoal
        fields = (
            'id', 'title', 'description', 'target_amount', 'current_amount',
            'remaining_amount', 'progress_percentage', 'is_completed',
            'deadline', 'status', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'current_amount', 'created_at', 'updated_at')
        extra_kwargs = {
            'title': {'required': False},
            'target_amount': {'required': False},
            'status': {'required': False},
            'deadline': {'required': False},
            'description': {'required': False},
        }


class GoalProgressSerializer(serializers.Serializer):
    """Overall progress of all goals"""
    total_goals = serializers.IntegerField()
    active_goals = serializers.IntegerField()
    completed_goals = serializers.IntegerField()
    total_saved = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_target = serializers.DecimalField(max_digits=12, decimal_places=2)
    overall_progress = serializers.FloatField()