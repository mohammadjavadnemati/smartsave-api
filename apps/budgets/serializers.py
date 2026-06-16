from rest_framework import serializers
from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    spent_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    usage_percentage = serializers.FloatField(read_only=True)
    alert_level = serializers.CharField(read_only=True)

    class Meta:
        model = Budget
        fields = (
            'id', 'category', 'category_name', 'category_slug',
            'amount', 'period', 'year', 'month', 'is_active',
            'spent_amount', 'remaining_amount', 'usage_percentage',
            'alert_level', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        user = self.context['request'].user

        category = attrs.get('category')
        if category and category.user != user:
            raise serializers.ValidationError(
                {'category': 'Invalid category'}
            )

        qs = Budget.objects.filter(
            user=user,
            category=attrs.get('category'),
            year=attrs.get('year'),
            month=attrs.get('month'),
            period=attrs.get('period'),
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'A budget for this category and period already exists'
            )
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BudgetUpdateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    spent_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    usage_percentage = serializers.FloatField(read_only=True)
    alert_level = serializers.CharField(read_only=True)

    class Meta:
        model = Budget
        fields = (
            'id', 'category', 'category_name', 'category_slug',
            'amount', 'period', 'year', 'month', 'is_active',
            'spent_amount', 'remaining_amount', 'usage_percentage',
            'alert_level', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'category': {'required': False},
            'amount': {'required': False},
            'period': {'required': False},
            'year': {'required': False},
            'month': {'required': False},
            'is_active': {'required': False},
        }


class BudgetAlertSerializer(serializers.Serializer):
    """Budget alerts"""
    budget_id = serializers.IntegerField()
    category_name = serializers.CharField()
    category_slug = serializers.CharField()
    alert_level = serializers.CharField()
    usage_percentage = serializers.FloatField()
    spent_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    budget_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    message = serializers.CharField()


class BudgetSummarySerializer(serializers.Serializer):
    """Monthly budget summary"""
    total_budget = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_remaining = serializers.DecimalField(max_digits=12, decimal_places=2)
    overall_usage_percentage = serializers.FloatField()
    budgets_on_track = serializers.IntegerField()
    budgets_warning = serializers.IntegerField()
    budgets_exceeded = serializers.IntegerField()
    alerts = BudgetAlertSerializer(many=True)