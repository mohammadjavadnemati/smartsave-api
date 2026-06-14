import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.tests.factories import UserFactory
from apps.incomes.models import IncomeSource, Income
from .factories import IncomeSourceFactory, IncomeFactory


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
class TestIncomeSourceViewSet:

    def test_list_sources(self, auth_client):
        client, user = auth_client
        IncomeSourceFactory.create_batch(3, user=user)
        url = reverse('incomes:source-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_source(self, auth_client):
        client, user = auth_client
        url = reverse('incomes:source-list')
        data = {'name': 'YouTube', 'slug': 'youtube'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert IncomeSource.objects.filter(user=user, slug='youtube').exists()

    def test_cannot_delete_default_source(self, auth_client):
        client, user = auth_client
        source = IncomeSourceFactory(user=user, is_default=True)
        url = reverse('incomes:source-detail', kwargs={'pk': source.pk})
        response = client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_partial_update_source(self, auth_client):
        client, user = auth_client
        source = IncomeSourceFactory(user=user, name='Old Name')
        url = reverse('incomes:source-detail', kwargs={'pk': source.pk})
        response = client.patch(url, {'name': 'New Name'})
        assert response.status_code == status.HTTP_200_OK
        source.refresh_from_db()
        assert source.name == 'New Name'


@pytest.mark.django_db
class TestIncomeViewSet:

    def test_list_incomes(self, auth_client):
        client, user = auth_client
        IncomeFactory.create_batch(5, user=user)
        url = reverse('incomes:income-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5

    def test_create_income(self, auth_client):
        client, user = auth_client
        source = IncomeSourceFactory(user=user)
        url = reverse('incomes:income-list')
        data = {
            'amount': '3000.00',
            'description': 'Monthly salary',
            'date': '2026-06-01',
            'source': source.pk,
            'is_recurring': True,
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Income.objects.filter(user=user).count() == 1

    def test_partial_update_income(self, auth_client):
        client, user = auth_client
        income = IncomeFactory(user=user, amount=Decimal('1000.00'))
        url = reverse('incomes:income-detail', kwargs={'pk': income.pk})
        response = client.patch(url, {'amount': '1500.00'})
        assert response.status_code == status.HTTP_200_OK
        income.refresh_from_db()
        assert income.amount == Decimal('1500.00')

    def test_cannot_access_other_user_income(self, auth_client, db):
        client, user = auth_client
        other_user = UserFactory()
        income = IncomeFactory(user=other_user)
        url = reverse('incomes:income-detail', kwargs={'pk': income.pk})
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_filter_by_month(self, auth_client):
        client, user = auth_client
        import datetime
        IncomeFactory(user=user, date=datetime.date(2026, 1, 15))
        IncomeFactory(user=user, date=datetime.date(2026, 6, 1))
        url = reverse('incomes:income-list')
        response = client.get(url, {'month': 6})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_summary(self, auth_client):
        client, user = auth_client
        IncomeFactory.create_batch(3, user=user, amount=Decimal('1000.00'))
        url = reverse('incomes:income-summary')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['income_count'] == 3
        assert Decimal(response.data['total_amount']) == Decimal('3000.00')

    def test_monthly_report(self, auth_client):
        client, user = auth_client
        import datetime
        IncomeFactory(user=user, date=datetime.date(2026, 1, 15), amount=Decimal('1000.00'))
        IncomeFactory(user=user, date=datetime.date(2026, 6, 1), amount=Decimal('2000.00'))
        url = reverse('incomes:income-monthly-report')
        response = client.get(url, {'year': 2026})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_vs_expenses(self, auth_client):
        client, user = auth_client
        import datetime
        IncomeFactory(user=user, date=datetime.date(2026, 6, 1), amount=Decimal('3000.00'))
        url = reverse('incomes:income-vs-expenses')
        response = client.get(url, {'year': 2026})
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['income'] == Decimal('3000.00')
        assert 'savings_rate' in response.data[0]