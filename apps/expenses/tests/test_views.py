import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.tests.factories import UserFactory
from apps.expenses.models import Category, Expense
from .factories import CategoryFactory, ExpenseFactory


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
class TestCategoryViewSet:

    def test_list_categories(self, auth_client):
        client, user = auth_client
        CategoryFactory.create_batch(3, user=user)
        url = reverse('expenses:category-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_category(self, auth_client):
        client, user = auth_client
        url = reverse('expenses:category-list')
        data = {'name': 'Gaming', 'slug': 'gaming', 'icon': '🎮'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Category.objects.filter(user=user, slug='gaming').exists()

    def test_cannot_delete_default_category(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user, is_default=True)
        url = reverse('expenses:category-detail', kwargs={'pk': category.pk})
        response = client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_can_delete_custom_category(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user, is_default=False)
        url = reverse('expenses:category-detail', kwargs={'pk': category.pk})
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestExpenseViewSet:

    def test_list_expenses(self, auth_client):
        client, user = auth_client
        ExpenseFactory.create_batch(5, user=user)
        url = reverse('expenses:expense-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5

    def test_create_expense(self, auth_client):
        client, user = auth_client
        category = CategoryFactory(user=user)
        url = reverse('expenses:expense-list')
        data = {
            'amount': '50.00',
            'description': 'Grocery shopping',
            'date': '2026-06-13',
            'category': category.pk,
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Expense.objects.filter(user=user).count() == 1

    def test_cannot_access_other_user_expense(self, auth_client, db):
        client, user = auth_client
        other_user = UserFactory()
        expense = ExpenseFactory(user=other_user)
        url = reverse('expenses:expense-detail', kwargs={'pk': expense.pk})
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_filter_by_date_range(self, auth_client):
        client, user = auth_client
        import datetime
        ExpenseFactory(user=user, date=datetime.date(2026, 1, 15))
        ExpenseFactory(user=user, date=datetime.date(2026, 3, 10))
        ExpenseFactory(user=user, date=datetime.date(2026, 6, 1))
        url = reverse('expenses:expense-list')
        response = client.get(url, {'date_from': '2026-03-01', 'date_to': '2026-06-30'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_search_expenses(self, auth_client):
        client, user = auth_client
        ExpenseFactory(user=user, description='cigarette pack')
        ExpenseFactory(user=user, description='grocery shopping')
        url = reverse('expenses:expense-list')
        response = client.get(url, {'search': 'cigarette'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_savings_impact(self, auth_client):
        client, user = auth_client
        ExpenseFactory(
            user=user,
            description='cigarette pack',
            amount=Decimal('50.00')
        )
        ExpenseFactory(
            user=user,
            description='cigarette box',
            amount=Decimal('30.00')
        )
        url = reverse('expenses:expense-savings-impact')
        response = client.get(url, {'q': 'cigarette'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['transaction_count'] == 2
        assert 'savings_impact' in response.data
        assert '1_year' in response.data['savings_impact']

    def test_summary(self, auth_client):
        client, user = auth_client
        ExpenseFactory.create_batch(3, user=user, amount=Decimal('100.00'))
        url = reverse('expenses:expense-summary')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['expense_count'] == 3
        assert Decimal(response.data['total_amount']) == Decimal('300.00')