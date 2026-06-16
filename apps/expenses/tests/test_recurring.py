import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.tests.factories import UserFactory
from apps.expenses.models import RecurringExpense, Expense
from apps.expenses.tests.factories import CategoryFactory


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
class TestRecurringExpenseViewSet:

    def test_create_recurring(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        url = reverse('expenses:recurring-list')
        data = {
            'title': 'Netflix',
            'amount': '15.99',
            'frequency': 'monthly',
            'start_date': '2026-01-01',
            'category': category.pk,
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert RecurringExpense.objects.filter(user=user, title='Netflix').exists()

    def test_monthly_cost_calculation(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        url = reverse('expenses:recurring-list')
        data = {
            'title': 'Annual subscription',
            'amount': '120.00',
            'frequency': 'yearly',
            'start_date': '2026-01-01',
            'category': category.pk,
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data['monthly_cost']) == Decimal('10.00')
        assert Decimal(response.data['annual_cost']) == Decimal('120.00')

    def test_auto_generate_on_list(self, auth_client):
        """Test that recurring expenses are automatically generated"""
        client, user = auth_client
        category = CategoryFactory(user=user)
        RecurringExpense.objects.create(
            user=user,
            category=category,
            title='Internet',
            amount=Decimal('50.00'),
            frequency=RecurringExpense.Frequency.MONTHLY,
            start_date=date(2026, 1, 1),
            is_active=True,
            last_generated=None,
        )
        assert Expense.objects.filter(user=user).count() == 0

        url = reverse('expenses:expense-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert Expense.objects.filter(
            user=user, description='[Recurring] Internet'
        ).count() == 1

    def test_summary(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        RecurringExpense.objects.create(
            user=user, category=category,
            title='Netflix', amount=Decimal('15.00'),
            frequency=RecurringExpense.Frequency.MONTHLY,
            start_date=date(2026, 1, 1), is_active=True,
        )
        RecurringExpense.objects.create(
            user=user, category=category,
            title='Gym', amount=Decimal('30.00'),
            frequency=RecurringExpense.Frequency.MONTHLY,
            start_date=date(2026, 1, 1), is_active=True,
        )
        url = reverse('expenses:recurring-summary')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['active_count'] == 2
        assert Decimal(response.data['total_monthly_cost']) == Decimal('45.00')

    def test_partial_update_recurring(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        recurring = RecurringExpense.objects.create(
            user=user, category=category,
            title='Netflix', amount=Decimal('15.00'),
            frequency=RecurringExpense.Frequency.MONTHLY,
            start_date=date(2026, 1, 1),
        )
        url = reverse('expenses:recurring-detail', kwargs={'pk': recurring.pk})
        response = client.patch(url, {'amount': '18.00'})
        assert response.status_code == status.HTTP_200_OK
        recurring.refresh_from_db()
        assert recurring.amount == Decimal('18.00')