import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from decimal import Decimal
from apps.accounts.tests.factories import UserFactory
from apps.savings.models import SavingsGoal, SavingsDeposit


class SavingsGoalFactory(DjangoModelFactory):
    class Meta:
        model = SavingsGoal

    user = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f'Goal {n}')
    description = factory.Faker('sentence')
    target_amount = factory.Faker(
        'pydecimal', left_digits=4, right_digits=2, positive=True, min_value=100
    )
    current_amount = Decimal('0.00')
    status = SavingsGoal.Status.ACTIVE


class SavingsDepositFactory(DjangoModelFactory):
    class Meta:
        model = SavingsDeposit

    goal = factory.SubFactory(SavingsGoalFactory)
    amount = factory.Faker(
        'pydecimal', left_digits=3, right_digits=2, positive=True
    )
    note = factory.Faker('sentence')
    date = factory.Faker('date_this_year')