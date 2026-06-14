import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.tests.factories import UserFactory
from apps.savings.models import SavingsGoal, SavingsDeposit
from .factories import SavingsGoalFactory, SavingsDepositFactory


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
class TestSavingsGoalViewSet:

    def test_create_goal(self, auth_client):
        client, user = auth_client
        url = reverse('savings:goal-list')
        data = {
            'title': 'Buy a car',
            'target_amount': '10000.00',
            'deadline': '2027-01-01',
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert SavingsGoal.objects.filter(user=user, title='Buy a car').exists()

    def test_list_goals(self, auth_client):
        client, user = auth_client
        SavingsGoalFactory.create_batch(3, user=user)
        url = reverse('savings:goal-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_progress_percentage(self, auth_client):
        client, user = auth_client
        goal = SavingsGoalFactory(
            user=user,
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('250.00')
        )
        url = reverse('savings:goal-detail', kwargs={'pk': goal.pk})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['progress_percentage'] == 25.0

    def test_partial_update_goal(self, auth_client):
        client, user = auth_client
        goal = SavingsGoalFactory(user=user, title='Old Title')
        url = reverse('savings:goal-detail', kwargs={'pk': goal.pk})
        response = client.patch(url, {'title': 'New Title'})
        assert response.status_code == status.HTTP_200_OK
        goal.refresh_from_db()
        assert goal.title == 'New Title'

    def test_filter_by_status(self, auth_client):
        client, user = auth_client
        SavingsGoalFactory(user=user, status=SavingsGoal.Status.ACTIVE)
        SavingsGoalFactory(user=user, status=SavingsGoal.Status.COMPLETED)
        url = reverse('savings:goal-list')
        response = client.get(url, {'status': 'active'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_predict_months(self, auth_client):
        client, user = auth_client
        goal = SavingsGoalFactory(
            user=user,
            target_amount=Decimal('10000.00'),
            current_amount=Decimal('0.00')
        )
        url = reverse('savings:goal-predict', kwargs={'pk': goal.pk})
        response = client.get(url, {'monthly_saving': '250'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['months_to_goal'] == 40
        assert 'message' in response.data

    def test_overall_progress(self, auth_client):
        client, user = auth_client
        SavingsGoalFactory(
            user=user,
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('500.00')
        )
        SavingsGoalFactory(
            user=user,
            target_amount=Decimal('2000.00'),
            current_amount=Decimal('1000.00'),
            status=SavingsGoal.Status.COMPLETED
        )
        url = reverse('savings:goal-progress')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_goals'] == 2
        assert response.data['overall_progress'] == 50.0

    def test_cannot_access_other_user_goal(self, auth_client, db):
        client, user = auth_client
        other_user = UserFactory()
        goal = SavingsGoalFactory(user=other_user)
        url = reverse('savings:goal-detail', kwargs={'pk': goal.pk})
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSavingsDepositViewSet:

    def test_create_deposit_updates_goal(self, auth_client):
        client, user = auth_client
        goal = SavingsGoalFactory(
            user=user,
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('0.00')
        )
        url = reverse('savings:deposit-list')
        data = {
            'goal': goal.pk,
            'amount': '250.00',
            'note': 'First deposit',
            'date': '2026-06-14',
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        goal.refresh_from_db()
        assert goal.current_amount == Decimal('250.00')

    def test_goal_auto_completes(self, auth_client):
        client, user = auth_client
        goal = SavingsGoalFactory(
            user=user,
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('900.00')
        )
        url = reverse('savings:deposit-list')
        data = {
            'goal': goal.pk,
            'amount': '100.00',
            'note': 'Final deposit',
            'date': '2026-06-14',
        }
        client.post(url, data)
        goal.refresh_from_db()
        assert goal.status == SavingsGoal.Status.COMPLETED

    def test_delete_deposit_updates_goal(self, auth_client):
        client, user = auth_client
        goal = SavingsGoalFactory(
            user=user,
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('250.00')
        )
        deposit = SavingsDepositFactory(goal=goal, amount=Decimal('250.00'))
        url = reverse('savings:deposit-detail', kwargs={'pk': deposit.pk})
        client.delete(url)
        goal.refresh_from_db()
        assert goal.current_amount == Decimal('0.00')

    def test_cannot_deposit_to_cancelled_goal(self, auth_client):
        client, user = auth_client
        goal = SavingsGoalFactory(
            user=user,
            status=SavingsGoal.Status.CANCELLED
        )
        url = reverse('savings:deposit-list')
        data = {
            'goal': goal.pk,
            'amount': '100.00',
            'date': '2026-06-14',
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST