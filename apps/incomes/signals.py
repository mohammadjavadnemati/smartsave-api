from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import IncomeSource

User = get_user_model()


@receiver(post_save, sender=User)
def create_default_income_sources(sender, instance, created, **kwargs):
    """When a new user is created, default income sources are created for them"""
    if created:
        IncomeSource.create_defaults_for_user(instance)