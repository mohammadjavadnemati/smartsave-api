from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class IncomeSource(models.Model):
    # منابع درآمدی پیش‌فرض
    DEFAULT_SOURCES = [
        ('salary', 'Salary'),
        ('freelance', 'Freelance'),
        ('investment', 'Investment'),
        ('side_income', 'Side Income'),
        ('rental', 'Rental'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='income_sources'
    )
    name = models.CharField(max_length=100, verbose_name='name')
    slug = models.CharField(max_length=100, verbose_name='slug')
    is_default = models.BooleanField(default=False, verbose_name='is default')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'income source'
        verbose_name_plural = 'income sources'
        unique_together = ('user', 'slug')

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults_for_user(cls, user):
        """ساخت منابع درآمدی پیش‌فرض برای کاربر جدید"""
        defaults = [
            cls(user=user, name=name, slug=slug, is_default=True)
            for slug, name in cls.DEFAULT_SOURCES
        ]
        cls.objects.bulk_create(defaults, ignore_conflicts=True)


class Income(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='incomes'
    )
    source = models.ForeignKey(
        IncomeSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incomes'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='amount'
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='description'
    )
    date = models.DateField(verbose_name='date')
    is_recurring = models.BooleanField(
        default=False,
        verbose_name='is recurring'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'income'
        verbose_name_plural = 'incomes'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.amount} - {self.date}'