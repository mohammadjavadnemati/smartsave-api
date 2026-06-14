from rest_framework import serializers
from .models import Income, IncomeSource


class IncomeSourceSerializer(serializers.ModelSerializer):
    income_count = serializers.IntegerField(read_only=True, default=0)
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        default=0
    )

    class Meta:
        model = IncomeSource
        fields = ('id', 'name', 'slug', 'is_default', 'income_count', 'total_amount')
        read_only_fields = ('id', 'is_default')

    def validate_slug(self, value):
        user = self.context['request'].user
        qs = IncomeSource.objects.filter(user=user, slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'An income source with this slug already exists'
            )
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class IncomeSourceUpdateSerializer(serializers.ModelSerializer):
    income_count = serializers.IntegerField(read_only=True, default=0)
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        default=0
    )

    class Meta:
        model = IncomeSource
        fields = ('id', 'name', 'slug', 'is_default', 'income_count', 'total_amount')
        read_only_fields = ('id', 'is_default')
        extra_kwargs = {
            'name': {'required': False},
            'slug': {'required': False},
        }

    def validate_slug(self, value):
        user = self.context['request'].user
        qs = IncomeSource.objects.filter(user=user, slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'An income source with this slug already exists'
            )
        return value


class IncomeCreateSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_slug = serializers.CharField(source='source.slug', read_only=True)

    class Meta:
        model = Income
        fields = (
            'id', 'source', 'source_name', 'source_slug',
            'amount', 'description', 'date', 'is_recurring',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_source(self, value):
        user = self.context['request'].user
        if value and value.user != user:
            raise serializers.ValidationError('Invalid income source')
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class IncomeUpdateSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_slug = serializers.CharField(source='source.slug', read_only=True)

    class Meta:
        model = Income
        fields = (
            'id', 'source', 'source_name', 'source_slug',
            'amount', 'description', 'date', 'is_recurring',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'source': {'required': False},
            'amount': {'required': False},
            'description': {'required': False},
            'date': {'required': False},
            'is_recurring': {'required': False},
        }

    def validate_source(self, value):
        user = self.context['request'].user
        if value and value.user != user:
            raise serializers.ValidationError('Invalid income source')
        return value


class IncomeSummarySerializer(serializers.Serializer):
    """خلاصه درآمدها برای داشبورد"""
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    income_count = serializers.IntegerField()
    average_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_source = IncomeSourceSerializer(many=True)


class MonthlyIncomeReportSerializer(serializers.Serializer):
    """گزارش درآمد ماهانه"""
    month = serializers.DateField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    income_count = serializers.IntegerField()