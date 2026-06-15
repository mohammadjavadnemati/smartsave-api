from rest_framework import serializers


class FinancialHealthSerializer(serializers.Serializer):
    """امتیاز سلامت مالی کاربر"""
    score = serializers.IntegerField()
    level = serializers.CharField()
    breakdown = serializers.DictField()
    suggestions = serializers.ListField(child=serializers.CharField())


class DashboardSerializer(serializers.Serializer):
    """داشبورد اصلی"""
    # درآمد و هزینه
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_savings = serializers.DecimalField(max_digits=12, decimal_places=2)
    savings_rate = serializers.FloatField()

    # مقایسه با ماه قبل
    income_change_percentage = serializers.FloatField()
    expense_change_percentage = serializers.FloatField()
    savings_change_percentage = serializers.FloatField()

    # بودجه
    total_budget = serializers.DecimalField(max_digits=12, decimal_places=2)
    budget_usage_percentage = serializers.FloatField()
    budgets_exceeded = serializers.IntegerField()

    # اهداف پس‌انداز
    active_goals = serializers.IntegerField()
    completed_goals = serializers.IntegerField()

    # هشدارها
    alerts_count = serializers.IntegerField()

    # سلامت مالی
    financial_health_score = serializers.IntegerField()


class MonthlyTrendSerializer(serializers.Serializer):
    """روند ماهانه درآمد و هزینه"""
    month = serializers.DateField()
    income = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    savings = serializers.DecimalField(max_digits=12, decimal_places=2)
    savings_rate = serializers.FloatField()


class CategoryExpenseSerializer(serializers.Serializer):
    """هزینه بر اساس دسته‌بندی"""
    category_name = serializers.CharField()
    category_slug = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    percentage = serializers.FloatField()
    expense_count = serializers.IntegerField()


class SmartInsightSerializer(serializers.Serializer()):
    """تحلیل هوشمند مالی"""
    type = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField()
    impact = serializers.CharField()