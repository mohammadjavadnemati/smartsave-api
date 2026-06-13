from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Category

User = get_user_model()


@receiver(post_save, sender=User)
def create_default_categories(sender, instance, created, **kwargs):
    """وقتی کاربر جدید ساخته میشه، دسته‌بندی‌های پیش‌فرض براش میسازیم"""
    if created:
        Category.create_defaults_for_user(instance)