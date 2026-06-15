from decimal import Decimal
from datetime import date
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.expenses.models import Expense, Category
from apps.incomes.models import Income
from apps.savings.models import SavingsGoal
from apps.budgets.models import Budget


def get_month_range(year: int, month: int):
    """برگرداندن اول و آخر ماه"""
    import calendar
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


def calculate_financial_health_score(
    savings_rate: float,
    budget_adherence: float,
    income_stability: float,
    expense_to_income: float,
) -> dict:
    """
    محاسبه امتیاز سلامت مالی بین ۰ تا ۱۰۰
    فاکتورها:
    - نرخ پس‌انداز (۳۰ امتیاز)
    - رعایت بودجه (۳۰ امتیاز)
    - ثبات درآمد (۲۰ امتیاز)
    - نسبت هزینه به درآمد (۲۰ امتیاز)
    """
    # امتیاز نرخ پس‌انداز
    if savings_rate >= 20:
        savings_score = 30
    elif savings_rate >= 10:
        savings_score = 20
    elif savings_rate >= 5:
        savings_score = 10
    else:
        savings_score = 0

    # امتیاز رعایت بودجه
    if budget_adherence >= 90:
        budget_score = 30
    elif budget_adherence >= 70:
        budget_score = 20
    elif budget_adherence >= 50:
        budget_score = 10
    else:
        budget_score = 0

    # امتیاز ثبات درآمد
    if income_stability >= 80:
        income_score = 20
    elif income_stability >= 60:
        income_score = 13
    elif income_stability >= 40:
        income_score = 7
    else:
        income_score = 0

    # امتیاز نسبت هزینه به درآمد
    if expense_to_income <= 50:
        expense_score = 20
    elif expense_to_income <= 70:
        expense_score = 13
    elif expense_to_income <= 90:
        expense_score = 7
    else:
        expense_score = 0

    total_score = savings_score + budget_score + income_score + expense_score

    if total_score >= 80:
        level = 'Excellent'
    elif total_score >= 60:
        level = 'Good'
    elif total_score >= 40:
        level = 'Fair'
    else:
        level = 'Poor'

    return {
        'score': total_score,
        'level': level,
        'breakdown': {
            'savings_rate_score': savings_score,
            'budget_adherence_score': budget_score,
            'income_stability_score': income_score,
            'expense_ratio_score': expense_score,
        }
    }


@extend_schema(tags=['Analytics'])
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Main financial dashboard',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, description='Year (default: current year)'),
            OpenApiParameter('month', OpenApiTypes.INT, description='Month (default: current month)'),
        ],
    )
    def get(self, request):
        """داشبورد اصلی مالی"""
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))

        first_day, last_day = get_month_range(year, month)

        # ماه قبل
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        prev_first, prev_last = get_month_range(prev_year, prev_month)

        # درآمد و هزینه ماه جاری
        current_income = Income.objects.filter(
            user=request.user, date__range=(first_day, last_day)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        current_expense = Expense.objects.filter(
            user=request.user, date__range=(first_day, last_day)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # درآمد و هزینه ماه قبل
        prev_income = Income.objects.filter(
            user=request.user, date__range=(prev_first, prev_last)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        prev_expense = Expense.objects.filter(
            user=request.user, date__range=(prev_first, prev_last)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # محاسبه پس‌انداز
        current_savings = current_income - current_expense
        prev_savings = prev_income - prev_expense

        # نرخ پس‌انداز
        savings_rate = (
            round(float(current_savings / current_income * 100), 2)
            if current_income > 0 else 0
        )

        # درصد تغییر نسبت به ماه قبل
        def change_percentage(current, previous):
            if previous == 0:
                return 0
            return round(float((current - previous) / previous * 100), 2)

        # بودجه ماه جاری
        budgets = Budget.objects.filter(
            user=request.user, year=year, month=month, is_active=True
        ).select_related('category')

        total_budget = sum(b.amount for b in budgets)
        total_budget_spent = sum(b.spent_amount for b in budgets)
        budgets_exceeded = sum(1 for b in budgets if b.alert_level == 'exceeded')
        budget_usage = (
            round(float(total_budget_spent / total_budget * 100), 2)
            if total_budget > 0 else 0
        )

        # اهداف پس‌انداز
        goals = SavingsGoal.objects.filter(user=request.user)
        active_goals = goals.filter(status=SavingsGoal.Status.ACTIVE).count()
        completed_goals = goals.filter(status=SavingsGoal.Status.COMPLETED).count()

        # تعداد هشدارها
        alerts_count = sum(
            1 for b in budgets if b.alert_level != 'none'
        )

        # امتیاز سلامت مالی
        expense_to_income = (
            float(current_expense / current_income * 100)
            if current_income > 0 else 100
        )
        budget_adherence = 100 - budget_usage if budget_usage <= 100 else 0
        health = calculate_financial_health_score(
            savings_rate=savings_rate,
            budget_adherence=budget_adherence,
            income_stability=80,
            expense_to_income=expense_to_income,
        )

        return Response({
            'period': {'year': year, 'month': month},
            'total_income': current_income,
            'total_expense': current_expense,
            'total_savings': current_savings,
            'savings_rate': savings_rate,
            'income_change_percentage': change_percentage(current_income, prev_income),
            'expense_change_percentage': change_percentage(current_expense, prev_expense),
            'savings_change_percentage': change_percentage(current_savings, prev_savings),
            'total_budget': total_budget,
            'budget_usage_percentage': budget_usage,
            'budgets_exceeded': budgets_exceeded,
            'active_goals': active_goals,
            'completed_goals': completed_goals,
            'alerts_count': alerts_count,
            'financial_health_score': health['score'],
            'financial_health_level': health['level'],
        })


@extend_schema(tags=['Analytics'])
class MonthlyTrendView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Monthly income and expense trend',
        parameters=[
            OpenApiParameter('months', OpenApiTypes.INT, description='Number of months (default: 6)'),
        ],
    )
    def get(self, request):
        """روند ماهانه درآمد، هزینه و پس‌انداز"""
        months_count = int(request.query_params.get('months', 6))
        months_count = min(months_count, 24)

        # درآمد ماهانه
        monthly_income = {
            item['month']: item['total']
            for item in Income.objects.filter(
                user=request.user
            ).annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('-month')[:months_count]
        }

        # هزینه ماهانه
        monthly_expense = {
            item['month']: item['total']
            for item in Expense.objects.filter(
                user=request.user
            ).annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('-month')[:months_count]
        }

        all_months = sorted(
            set(list(monthly_income.keys()) + list(monthly_expense.keys()))
        )

        result = []
        for month in all_months:
            income = monthly_income.get(month, Decimal('0'))
            expense = monthly_expense.get(month, Decimal('0'))
            savings = income - expense
            savings_rate = (
                round(float(savings / income * 100), 2)
                if income > 0 else 0
            )
            result.append({
                'month': month,
                'income': income,
                'expense': expense,
                'savings': savings,
                'savings_rate': savings_rate,
            })

        return Response(result)


@extend_schema(tags=['Analytics'])
class CategoryExpenseView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Expense breakdown by category',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, description='Year (default: current year)'),
            OpenApiParameter('month', OpenApiTypes.INT, description='Month (default: current month)'),
            OpenApiParameter('period', OpenApiTypes.STR, description='Period: monthly/yearly (default: monthly)'),
        ],
    )
    def get(self, request):
        """توزیع هزینه‌ها بر اساس دسته‌بندی"""
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        period = request.query_params.get('period', 'monthly')

        filters = {'user': request.user, 'date__year': year}
        if period == 'monthly':
            filters['date__month'] = month

        total = Expense.objects.filter(**filters).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('1')

        by_category = Expense.objects.filter(**filters).values(
            'category__name', 'category__slug'
        ).annotate(
            total_amount=Sum('amount'),
            expense_count=Count('id'),
        ).order_by('-total_amount')

        result = []
        for item in by_category:
            result.append({
                'category_name': item['category__name'] or 'Uncategorized',
                'category_slug': item['category__slug'] or 'uncategorized',
                'total_amount': item['total_amount'],
                'percentage': round(float(item['total_amount'] / total * 100), 2),
                'expense_count': item['expense_count'],
            })

        return Response(result)


@extend_schema(tags=['Analytics'])
class FinancialHealthView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Financial health score',
        parameters=[
            OpenApiParameter('months', OpenApiTypes.INT, description='Months to analyze (default: 3)'),
        ],
    )
    def get(self, request):
        """امتیاز سلامت مالی با پیشنهادهای بهبود"""
        months_count = int(request.query_params.get('months', 3))
        now = timezone.now()

        # میانگین درآمد و هزینه چند ماه اخیر
        from dateutil.relativedelta import relativedelta
        start_date = (now - relativedelta(months=months_count)).date()

        total_income = Income.objects.filter(
            user=request.user, date__gte=start_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        total_expense = Expense.objects.filter(
            user=request.user, date__gte=start_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        avg_monthly_income = total_income / months_count
        avg_monthly_expense = total_expense / months_count
        avg_savings = avg_monthly_income - avg_monthly_expense

        savings_rate = (
            float(avg_savings / avg_monthly_income * 100)
            if avg_monthly_income > 0 else 0
        )
        expense_to_income = (
            float(avg_monthly_expense / avg_monthly_income * 100)
            if avg_monthly_income > 0 else 100
        )

        # بودجه‌بندی
        budgets = Budget.objects.filter(
            user=request.user, is_active=True
        ).select_related('category')
        exceeded_count = sum(1 for b in budgets if b.alert_level == 'exceeded')
        total_budgets = budgets.count()
        budget_adherence = (
            (total_budgets - exceeded_count) / total_budgets * 100
            if total_budgets > 0 else 50
        )

        # درآمد ماهانه
        monthly_incomes = Income.objects.filter(
            user=request.user, date__gte=start_date
        ).annotate(month=TruncMonth('date')).values('month').annotate(
            total=Sum('amount')
        ).values_list('total', flat=True)

        if len(monthly_incomes) > 1:
            avg = sum(monthly_incomes) / len(monthly_incomes)
            variance = sum((x - avg) ** 2 for x in monthly_incomes) / len(monthly_incomes)
            income_stability = max(0, 100 - float(variance ** 0.5 / avg * 100))
        else:
            income_stability = 50

        health = calculate_financial_health_score(
            savings_rate=savings_rate,
            budget_adherence=budget_adherence,
            income_stability=income_stability,
            expense_to_income=expense_to_income,
        )

        # پیشنهادهای هوشمند
        suggestions = []
        if savings_rate < 20:
            suggestions.append(
                f'Try to save at least 20% of your income. '
                f'Currently you are saving {savings_rate:.1f}%'
            )
        if exceeded_count > 0:
            suggestions.append(
                f'You have exceeded {exceeded_count} budget(s). '
                f'Review your spending in those categories'
            )
        if expense_to_income > 80:
            suggestions.append(
                f'Your expenses are {expense_to_income:.1f}% of your income. '
                f'Try to reduce spending to below 80%'
            )
        if not suggestions:
            suggestions.append('Great job! Keep maintaining your financial discipline.')

        return Response({
            **health,
            'analysis_period_months': months_count,
            'avg_monthly_income': avg_monthly_income,
            'avg_monthly_expense': avg_monthly_expense,
            'avg_monthly_savings': avg_savings,
            'savings_rate': round(savings_rate, 2),
            'expense_to_income_ratio': round(expense_to_income, 2),
            'budget_adherence': round(budget_adherence, 2),
            'income_stability': round(income_stability, 2),
            'suggestions': suggestions,
        })


@extend_schema(tags=['Analytics'])
class SmartInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Smart financial insights and suggestions',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, description='Year (default: current year)'),
            OpenApiParameter('month', OpenApiTypes.INT, description='Month (default: current month)'),
        ],
    )
    def get(self, request):
        """
        تحلیل هوشمند مالی:
        - بیشترین هزینه مربوط به خوراکی است
        - کاهش ۲۰٪ هزینه تفریح می‌تواند سالانه ۲۴۰ دلار صرفه‌جویی ایجاد کند
        - نرخ پس‌انداز شما نسبت به ماه قبل ۱۵٪ افزایش یافته است
        """
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))

        first_day, last_day = get_month_range(year, month)

        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        prev_first, prev_last = get_month_range(prev_year, prev_month)

        insights = []

        # درآمد و هزینه ماه جاری و قبلی
        current_income = Income.objects.filter(
            user=request.user, date__range=(first_day, last_day)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        current_expense = Expense.objects.filter(
            user=request.user, date__range=(first_day, last_day)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        prev_income = Income.objects.filter(
            user=request.user, date__range=(prev_first, prev_last)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        prev_expense = Expense.objects.filter(
            user=request.user, date__range=(prev_first, prev_last)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # بیشترین دسته هزینه
        top_category = Expense.objects.filter(
            user=request.user, date__range=(first_day, last_day)
        ).values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total').first()

        if top_category:
            insights.append({
                'type': 'info',
                'title': 'Top Spending Category',
                'message': (
                    f'Your highest spending this month is on '
                    f'{top_category["category__name"]} '
                    f'(${top_category["total"]:.2f})'
                ),
                'impact': 'neutral',
            })

        # مقایسه هزینه با ماه قبل
        if prev_expense > 0:
            expense_change = float(
                (current_expense - prev_expense) / prev_expense * 100
            )
            if expense_change > 10:
                insights.append({
                    'type': 'warning',
                    'title': 'Expenses Increased',
                    'message': (
                        f'Your expenses increased by {expense_change:.1f}% '
                        f'compared to last month'
                    ),
                    'impact': 'negative',
                })
            elif expense_change < -10:
                insights.append({
                    'type': 'success',
                    'title': 'Expenses Decreased',
                    'message': (
                        f'Great! Your expenses decreased by '
                        f'{abs(expense_change):.1f}% compared to last month'
                    ),
                    'impact': 'positive',
                })

        # مقایسه نرخ پس‌انداز
        current_savings_rate = (
            float((current_income - current_expense) / current_income * 100)
            if current_income > 0 else 0
        )
        prev_savings_rate = (
            float((prev_income - prev_expense) / prev_income * 100)
            if prev_income > 0 else 0
        )
        savings_rate_change = current_savings_rate - prev_savings_rate

        if abs(savings_rate_change) > 5:
            if savings_rate_change > 0:
                insights.append({
                    'type': 'success',
                    'title': 'Savings Rate Improved',
                    'message': (
                        f'Your savings rate increased by '
                        f'{savings_rate_change:.1f}% compared to last month'
                    ),
                    'impact': 'positive',
                })
            else:
                insights.append({
                    'type': 'warning',
                    'title': 'Savings Rate Dropped',
                    'message': (
                        f'Your savings rate decreased by '
                        f'{abs(savings_rate_change):.1f}% compared to last month'
                    ),
                    'impact': 'negative',
                })

        # پیشنهاد کاهش هزینه دسته‌ها
        by_category = Expense.objects.filter(
            user=request.user, date__range=(first_day, last_day)
        ).values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:3]

        for cat in by_category:
            saving_20_percent = float(cat['total']) * 0.20
            annual_saving = saving_20_percent * 12
            if annual_saving > 100:
                insights.append({
                    'type': 'tip',
                    'title': f'Reduce {cat["category__name"]} Spending',
                    'message': (
                        f'Reducing your {cat["category__name"]} expenses by 20% '
                        f'could save you ${annual_saving:.0f} annually'
                    ),
                    'impact': 'positive',
                })

        return Response(insights)