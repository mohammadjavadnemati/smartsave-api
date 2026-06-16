from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class SavingsGoal(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='savings_goals'
    )
    title = models.CharField(max_length=200, verbose_name='title')
    description = models.TextField(blank=True, verbose_name='description')
    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='target amount'
    )
    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='current amount'
    )
    deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name='deadline'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name='status'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'savings goal'
        verbose_name_plural = 'savings goals'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.title}'

    @property
    def progress_percentage(self):
        """Progress percentage toward the goal"""
        if self.target_amount <= 0:
            return 0
        percentage = (self.current_amount / self.target_amount) * 100
        return min(round(float(percentage), 2), 100)

    @property
    def remaining_amount(self):
        """Remaining amount to reach the goal"""
        remaining = self.target_amount - self.current_amount
        return max(remaining, Decimal('0.00'))

    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount


class SavingsDeposit(models.Model):
    """Whenever the user adds money to their goal"""
    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.CASCADE,
        related_name='deposits'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='amount'
    )
    note = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='note'
    )
    date = models.DateField(verbose_name='date')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'savings deposit'
        verbose_name_plural = 'savings deposits'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.goal.title} - {self.amount}'