import factory
from factory.django import DjangoModelFactory
from apps.accounts.tests.factories import UserFactory
from apps.incomes.models import IncomeSource, Income


class IncomeSourceFactory(DjangoModelFactory):
    class Meta:
        model = IncomeSource

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Source {n}')
    slug = factory.Sequence(lambda n: f'source-{n}')
    is_default = False


class IncomeFactory(DjangoModelFactory):
    class Meta:
        model = Income

    user = factory.SubFactory(UserFactory)
    source = factory.SubFactory(IncomeSourceFactory)
    amount = factory.Faker(
        'pydecimal', left_digits=4, right_digits=2, positive=True
    )
    description = factory.Faker('sentence')
    date = factory.Faker('date_this_year')
    is_recurring = False