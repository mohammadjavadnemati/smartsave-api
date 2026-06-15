import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.tests.factories import UserFactory
from apps.expenses.tests.factories import CategoryFactory, ExpenseFactory
from apps.budgets.models import Budget
from .factories import BudgetFactory
import datetime


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client, user


@pytest.mark.django_db
class TestBudgetViewSet:

    def test_create_budget(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        url = reverse('budgets:budget-list')
        data = {
            'category': category.pk,
            'amount': '300.00',
            'period': 'monthly',
            'year': 2026,
            'month': 6,
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Budget.objects.filter(user=user).count() == 1

    def test_duplicate_budget_rejected(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        BudgetFactory(user=user, category=category, year=2026, month=6)
        url = reverse('budgets:budget-list')
        data = {
            'category': category.pk,
            'amount': '500.00',
            'period': 'monthly',
            'year': 2026,
            'month': 6,
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_budget_usage_percentage(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        budget = BudgetFactory(
            user=user,
            category=category,
            amount=Decimal('300.00'),
            year=2026,
            month=6,
        )
        ExpenseFactory(
            user=user,
            category=category,
            amount=Decimal('240.00'),
            date=datetime.date(2026, 6, 1)
        )
        url = reverse('budgets:budget-detail', kwargs={'pk': budget.pk})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['usage_percentage'] == 80.0
        assert response.data['alert_level'] == 'warning'

    def test_budget_exceeded(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        budget = BudgetFactory(
            user=user,
            category=category,
            amount=Decimal('100.00'),
            year=2026,
            month=6,
        )
        ExpenseFactory(
            user=user,
            category=category,
            amount=Decimal('150.00'),
            date=datetime.date(2026, 6, 1)
        )
        url = reverse('budgets:budget-detail', kwargs={'pk': budget.pk})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['alert_level'] == 'exceeded'

    def test_alerts_endpoint(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        BudgetFactory(
            user=user,
            category=category,
            amount=Decimal('100.00'),
            year=2026,
            month=6,
        )
        ExpenseFactory(
            user=user,
            category=category,
            amount=Decimal('90.00'),
            date=datetime.date(2026, 6, 1)
        )
        url = reverse('budgets:budget-alerts')
        response = client.get(url, {'year': 2026, 'month': 6})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['alert_level'] == 'warning'

    def test_summary_endpoint(self, auth_client):
        client, user = auth_client
        category1 = CategoryFactory(user=user)
        category2 = CategoryFactory(user=user)
        BudgetFactory(
            user=user, category=category1,
            amount=Decimal('300.00'), year=2026, month=6
        )
        BudgetFactory(
            user=user, category=category2,
            amount=Decimal('200.00'), year=2026, month=6
        )
        ExpenseFactory(
            user=user, category=category1,
            amount=Decimal('270.00'), date=datetime.date(2026, 6, 1)
        )
        url = reverse('budgets:budget-summary')
        response = client.get(url, {'year': 2026, 'month': 6})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_budget'] == Decimal('500.00')
        assert response.data['budgets_warning'] == 1
        assert response.data['budgets_on_track'] == 1

    def test_partial_update_budget(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        budget = BudgetFactory(user=user, category=category, amount=Decimal('300.00'))
        url = reverse('budgets:budget-detail', kwargs={'pk': budget.pk})
        response = client.patch(url, {'amount': '500.00'})
        assert response.status_code == status.HTTP_200_OK
        budget.refresh_from_db()
        assert budget.amount == Decimal('500.00')