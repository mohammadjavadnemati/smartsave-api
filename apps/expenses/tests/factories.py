import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from apps.accounts.tests.factories import UserFactory
from apps.expenses.models import Category, Expense


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.Sequence(lambda n: f'category-{n}')
    is_default = False


class ExpenseFactory(DjangoModelFactory):
    class Meta:
        model = Expense

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    amount = factory.Faker(
        'pydecimal', left_digits=4, right_digits=2, positive=True
    )
    description = factory.Faker('sentence')
    date = factory.Faker('date_this_year')
    is_recurring = False