import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from apps.accounts.tests.factories import UserFactory
from apps.expenses.tests.factories import CategoryFactory
from apps.budgets.models import Budget


class BudgetFactory(DjangoModelFactory):
    class Meta:
        model = Budget

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    amount = factory.Faker(
        'pydecimal', left_digits=3, right_digits=2, positive=True
    )
    period = Budget.Period.MONTHLY
    year = factory.LazyFunction(lambda: timezone.now().year)
    month = factory.LazyFunction(lambda: timezone.now().month)
    is_active = True