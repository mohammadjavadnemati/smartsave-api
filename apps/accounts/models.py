from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='email')
    first_name = models.CharField(max_length=100, blank=True, verbose_name='first name')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='last name')


    default_currency = models.CharField(
        max_length=3,
        default='USD',
        verbose_name='default currency'
    )
    monthly_income_goal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='monthly income goal'
    )
    savings_rate_goal = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Target savings rate percentage (e.g. 20 for 20%)',
        verbose_name='savings rate goal'
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email


class BlacklistedAccessToken(models.Model):
    jti = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'blacklisted access token'
        verbose_name_plural = 'blacklisted access tokens'

    def __str__(self):
        return self.jti

    @classmethod
    def is_blacklisted(cls, jti: str) -> bool:
        return cls.objects.filter(jti=jti).exists()