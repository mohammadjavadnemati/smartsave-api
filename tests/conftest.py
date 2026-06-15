import pytest
from decimal import Decimal
from datetime import date
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.tests.factories import UserFactory
from apps.expenses.tests.factories import CategoryFactory, ExpenseFactory
from apps.incomes.tests.factories import IncomeSourceFactory, IncomeFactory
from apps.savings.tests.factories import SavingsGoalFactory, SavingsDepositFactory
from apps.budgets.tests.factories import BudgetFactory


@pytest.fixture(scope='session')
def django_db_setup():
    pass


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def second_user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client, user


@pytest.fixture
def second_auth_client(second_user):
    client = APIClient()
    refresh = RefreshToken.for_user(second_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client, second_user


@pytest.fixture
def category(user, db):
    return CategoryFactory(user=user)


@pytest.fixture
def income_source(user, db):
    return IncomeSourceFactory(user=user)


@pytest.fixture
def expense(user, category, db):
    return ExpenseFactory(
        user=user,
        category=category,
        amount=Decimal('100.00'),
        date=date(2026, 6, 1)
    )


@pytest.fixture
def income(user, income_source, db):
    return IncomeFactory(
        user=user,
        source=income_source,
        amount=Decimal('3000.00'),
        date=date(2026, 6, 1)
    )


@pytest.fixture
def savings_goal(user, db):
    return SavingsGoalFactory(
        user=user,
        title='Buy a Laptop',
        target_amount=Decimal('2000.00'),
        current_amount=Decimal('0.00')
    )


@pytest.fixture
def budget(user, category, db):
    return BudgetFactory(
        user=user,
        category=category,
        amount=Decimal('500.00'),
        year=2026,
        month=6
    )