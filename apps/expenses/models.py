from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class Category(models.Model):
    # دسته‌بندی‌های پیش‌فرض سیستم
    DEFAULT_CATEGORIES = [
        ('food', 'Food'),
        ('transport', 'Transport'),
        ('entertainment', 'Entertainment'),
        ('clothing', 'Clothing'),
        ('health', 'Health'),
        ('education', 'Education'),
        ('bills', 'Bills'),
        ('cigarettes', 'Cigarettes'),
        ('travel', 'Travel'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='categories',
        help_text='Null means it is a default system category'
    )
    name = models.CharField(max_length=100, verbose_name='name')
    slug = models.CharField(max_length=100, verbose_name='slug')
    icon = models.CharField(max_length=50, blank=True, verbose_name='icon')
    is_default = models.BooleanField(default=False, verbose_name='is default')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'category'
        verbose_name_plural = 'categories'
        # هر کاربر نمی‌تونه دو دسته با یک اسم داشته باشه
        unique_together = ('user', 'slug')

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults_for_user(cls, user):
        """ساخت دسته‌بندی‌های پیش‌فرض برای کاربر جدید"""
        defaults = [
            cls(user=user, name=name, slug=slug, is_default=True)
            for slug, name in cls.DEFAULT_CATEGORIES
        ]
        cls.objects.bulk_create(defaults, ignore_conflicts=True)


class Expense(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
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
        verbose_name = 'expense'
        verbose_name_plural = 'expenses'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.amount} - {self.date}'