from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class Budget(models.Model):

    class Period(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        WEEKLY = 'weekly', 'Weekly'
        YEARLY = 'yearly', 'Yearly'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    category = models.ForeignKey(
        'expenses.Category',
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='budget amount'
    )
    period = models.CharField(
        max_length=10,
        choices=Period.choices,
        default=Period.MONTHLY,
        verbose_name='period'
    )
    year = models.IntegerField(verbose_name='year')
    month = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='month'
    )
    is_active = models.BooleanField(default=True, verbose_name='is active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'budget'
        verbose_name_plural = 'budgets'
        # هر کاربر برای هر دسته‌بندی در هر ماه فقط یه بودجه داره
        unique_together = ('user', 'category', 'year', 'month', 'period')
        ordering = ['-year', '-month']

    def __str__(self):
        return f'{self.user.email} - {self.category.name} - {self.amount}'

    @property
    def spent_amount(self):
        """مقدار خرج شده از این بودجه"""
        from apps.expenses.models import Expense
        from django.db.models import Sum

        filters = {
            'user': self.user,
            'category': self.category,
            'date__year': self.year,
        }
        if self.month:
            filters['date__month'] = self.month

        result = Expense.objects.filter(**filters).aggregate(
            total=Sum('amount')
        )
        return result['total'] or Decimal('0.00')

    @property
    def remaining_amount(self):
        """مقدار باقی‌مانده از بودجه"""
        remaining = self.amount - self.spent_amount
        return remaining

    @property
    def usage_percentage(self):
        """درصد استفاده از بودجه"""
        if self.amount <= 0:
            return 0
        percentage = (self.spent_amount / self.amount) * 100
        return round(float(percentage), 2)

    @property
    def alert_level(self):
        """
        سطح هشدار بودجه:
        - none: زیر ۸۰٪
        - warning: بین ۸۰٪ تا ۱۰۰٪
        - exceeded: بیشتر از ۱۰۰٪
        """
        usage = self.usage_percentage
        if usage >= 100:
            return 'exceeded'
        elif usage >= 80:
            return 'warning'
        return 'none'