from rest_framework import serializers
from .models import Expense, Category,RecurringExpense


class CategorySerializer(serializers.ModelSerializer):
    expense_count = serializers.IntegerField(read_only=True, default=0)
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        default=0
    )

    class Meta:
        model = Category
        fields = (
            'id', 'name', 'slug', 'icon',
            'is_default', 'expense_count', 'total_amount'
        )
        read_only_fields = ('id', 'is_default')
        # این رو اضافه کن
        extra_kwargs = {
            'name': {'required': False},
            'slug': {'required': False},
            'icon': {'required': False},
        }

    def validate_slug(self, value):
        user = self.context['request'].user
        qs = Category.objects.filter(user=user, slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'A category with this slug already exists'
            )
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ExpenseCreateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)

    class Meta:
        model = Expense
        fields = (
            'id', 'category', 'category_name', 'category_slug',
            'amount', 'description', 'date', 'is_recurring',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_category(self, value):
        user = self.context['request'].user
        if value and value.user != user:
            raise serializers.ValidationError('Invalid category')
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ExpenseUpdateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)

    class Meta:
        model = Expense
        fields = (
            'id', 'category', 'category_name', 'category_slug',
            'amount', 'description', 'date', 'is_recurring',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'category': {'required': False},
            'amount': {'required': False},
            'description': {'required': False},
            'date': {'required': False},
            'is_recurring': {'required': False},
        }

    def validate_category(self, value):
        user = self.context['request'].user
        if value and value.user != user:
            raise serializers.ValidationError('Invalid category')
        return value


class ExpenseSummarySerializer(serializers.Serializer):
    """خلاصه هزینه‌ها برای داشبورد"""
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense_count = serializers.IntegerField()
    average_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_category = CategorySerializer(many=True)


class SavingsImpactSerializer(serializers.Serializer):
    """
    نتیجه ماشین حساب تأثیر پس‌انداز
    کاربر سرچ می‌کنه مثلاً سیگار و میبینه اگه نخریده بود چقدر پول داشت
    """
    query = serializers.CharField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_average = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()
    transactions = ExpenseCreateSerializer(many=True)
    savings_impact = serializers.DictField()


class RecurringExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    monthly_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    annual_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = RecurringExpense
        fields = (
            'id', 'category', 'category_name', 'category_slug',
            'title', 'amount', 'description', 'frequency',
            'start_date', 'end_date', 'is_active',
            'monthly_cost', 'annual_cost',
            'last_generated', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'last_generated', 'created_at', 'updated_at')

    def validate_category(self, value):
        user = self.context['request'].user
        if value and value.user != user:
            raise serializers.ValidationError('Invalid category')
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class RecurringExpenseUpdateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    monthly_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    annual_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = RecurringExpense
        fields = (
            'id', 'category', 'category_name', 'category_slug',
            'title', 'amount', 'description', 'frequency',
            'start_date', 'end_date', 'is_active',
            'monthly_cost', 'annual_cost',
            'last_generated', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'last_generated', 'created_at', 'updated_at')
        extra_kwargs = {
            'title': {'required': False},
            'amount': {'required': False},
            'frequency': {'required': False},
            'start_date': {'required': False},
            'category': {'required': False},
            'is_active': {'required': False},
        }

    def validate_category(self, value):
        user = self.context['request'].user
        if value and value.user != user:
            raise serializers.ValidationError('Invalid category')
        return value


class RecurringSummarySerializer(serializers.Serializer):
    """خلاصه هزینه‌های تکرارشونده"""
    total_monthly_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_annual_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_count = serializers.IntegerField()
    by_frequency = serializers.DictField()
    items = RecurringExpenseSerializer(many=True)