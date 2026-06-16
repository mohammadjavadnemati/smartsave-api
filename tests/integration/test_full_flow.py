import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.tests.factories import UserFactory
from apps.expenses.tests.factories import CategoryFactory, ExpenseFactory
from apps.incomes.tests.factories import IncomeSourceFactory, IncomeFactory
from apps.savings.tests.factories import SavingsGoalFactory
from apps.budgets.tests.factories import BudgetFactory
from apps.expenses.models import RecurringExpense


@pytest.mark.django_db
class TestFullUserFlow:
    """
    End-to-end test of a user's workflow from registration to dashboard
    """

    def setup_method(self):
        self.client = APIClient()

    def test_complete_financial_flow(self):
        """
        Full workflow:
        1. Sign up
        2. Add income
        3. Add expense
        4. Create budget
        5. Create savings goal
        6. Deposit into goal
        7. Check dashboard
        """

        register_url = reverse('accounts:register')
        response = self.client.post(register_url, {
            'email': 'test@smartsave.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        })
        assert response.status_code == status.HTTP_201_CREATED
        access_token = response.data['tokens']['access']
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )

        source_url = reverse('incomes:source-list')
        source_response = self.client.post(source_url, {
            'name': 'Main Job',
            'slug': 'main-job',
        })
        assert source_response.status_code == status.HTTP_201_CREATED
        source_id = source_response.data['id']

        income_url = reverse('incomes:income-list')
        income_response = self.client.post(income_url, {
            'source': source_id,
            'amount': '5000.00',
            'description': 'Monthly salary',
            'date': '2026-06-01',
            'is_recurring': True,
        })
        assert income_response.status_code == status.HTTP_201_CREATED

        category_url = reverse('expenses:category-list')
        category_response = self.client.post(category_url, {
            'name': 'Groceries',
            'slug': 'groceries',
        })
        assert category_response.status_code == status.HTTP_201_CREATED
        category_id = category_response.data['id']

        expense_url = reverse('expenses:expense-list')
        expense_response = self.client.post(expense_url, {
            'category': category_id,
            'amount': '200.00',
            'description': 'Weekly groceries',
            'date': '2026-06-05',
        })
        assert expense_response.status_code == status.HTTP_201_CREATED

        budget_url = reverse('budgets:budget-list')
        budget_response = self.client.post(budget_url, {
            'category': category_id,
            'amount': '500.00',
            'period': 'monthly',
            'year': 2026,
            'month': 6,
        })
        assert budget_response.status_code == status.HTTP_201_CREATED

        budget_id = budget_response.data['id']
        budget_detail_url = reverse(
            'budgets:budget-detail', kwargs={'pk': budget_id}
        )
        budget_detail = self.client.get(budget_detail_url)
        assert budget_detail.data['usage_percentage'] == 40.0
        assert budget_detail.data['alert_level'] == 'none'

        goal_url = reverse('savings:goal-list')
        goal_response = self.client.post(goal_url, {
            'title': 'Emergency Fund',
            'target_amount': '10000.00',
            'deadline': '2027-12-31',
        })
        assert goal_response.status_code == status.HTTP_201_CREATED
        goal_id = goal_response.data['id']

        deposit_url = reverse('savings:deposit-list')
        deposit_response = self.client.post(deposit_url, {
            'goal': goal_id,
            'amount': '500.00',
            'note': 'First deposit',
            'date': '2026-06-15',
        })
        assert deposit_response.status_code == status.HTTP_201_CREATED

        goal_detail_url = reverse(
            'savings:goal-detail', kwargs={'pk': goal_id}
        )
        goal_detail = self.client.get(goal_detail_url)
        assert goal_detail.data['current_amount'] == '500.00'
        assert goal_detail.data['progress_percentage'] == 5.0

        dashboard_url = reverse('analytics:dashboard')
        dashboard_response = self.client.get(
            dashboard_url, {'year': 2026, 'month': 6}
        )
        assert dashboard_response.status_code == status.HTTP_200_OK
        assert Decimal(dashboard_response.data['total_income']) == Decimal('5000.00')
        assert Decimal(dashboard_response.data['total_expense']) == Decimal('200.00')
        assert Decimal(dashboard_response.data['total_savings']) == Decimal('4800.00')
        assert dashboard_response.data['savings_rate'] == 96.0
        assert dashboard_response.data['active_goals'] == 1


@pytest.mark.django_db
class TestUserDataIsolation:
    """
    Test that users cannot access each other's data
    """

    def test_expense_isolation(self, db):
        user1 = UserFactory()
        user2 = UserFactory()

        category1 = CategoryFactory(user=user1)
        category2 = CategoryFactory(user=user2)

        expense1 = ExpenseFactory(user=user1, category=category1)
        expense2 = ExpenseFactory(user=user2, category=category2)

        client1 = APIClient()
        refresh1 = RefreshToken.for_user(user1)
        client1.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh1.access_token}'
        )

        client2 = APIClient()
        refresh2 = RefreshToken.for_user(user2)
        client2.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh2.access_token}'
        )

        url = reverse('expenses:expense-list')
        response1 = client1.get(url)
        assert response1.data['count'] == 1
        assert response1.data['results'][0]['id'] == expense1.id

        response2 = client2.get(url)
        assert response2.data['count'] == 1
        assert response2.data['results'][0]['id'] == expense2.id

        detail_url = reverse(
            'expenses:expense-detail', kwargs={'pk': expense2.id}
        )
        response = client1.get(detail_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_savings_goal_isolation(self, db):
        user1 = UserFactory()
        user2 = UserFactory()

        goal1 = SavingsGoalFactory(user=user1)
        goal2 = SavingsGoalFactory(user=user2)

        client1 = APIClient()
        refresh1 = RefreshToken.for_user(user1)
        client1.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh1.access_token}'
        )

        url = reverse('savings:goal-list')
        response = client1.get(url)
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == goal1.id

    def test_budget_isolation(self, db):
        user1 = UserFactory()
        user2 = UserFactory()

        category1 = CategoryFactory(user=user1)
        category2 = CategoryFactory(user=user2)

        budget1 = BudgetFactory(user=user1, category=category1)
        budget2 = BudgetFactory(user=user2, category=category2)

        client1 = APIClient()
        refresh1 = RefreshToken.for_user(user1)
        client1.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh1.access_token}'
        )

        url = reverse('budgets:budget-list')
        response = client1.get(url)
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == budget1.id


@pytest.mark.django_db
class TestRecurringExpenseAutoGenerate:
    """Test auto-generation of recurring expenses"""

    def test_auto_generate_on_expense_list(self, db):
        user = UserFactory()
        category = CategoryFactory(user=user)

        RecurringExpense.objects.create(
            user=user,
            category=category,
            title='Netflix',
            amount=Decimal('15.00'),
            frequency=RecurringExpense.Frequency.MONTHLY,
            start_date=date(2026, 1, 1),
            is_active=True,
            last_generated=None,
        )

        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )

        from apps.expenses.models import Expense
        assert Expense.objects.filter(user=user).count() == 0

        url = reverse('expenses:expense-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert Expense.objects.filter(
            user=user,
            description='[Recurring] Netflix'
        ).count() == 1

    def test_no_duplicate_generation(self, db):
        """Should not be generated twice in the same month"""
        user = UserFactory()
        category = CategoryFactory(user=user)

        RecurringExpense.objects.create(
            user=user,
            category=category,
            title='Netflix',
            amount=Decimal('15.00'),
            frequency=RecurringExpense.Frequency.MONTHLY,
            start_date=date(2026, 1, 1),
            is_active=True,
            last_generated=date(2026, 6, 1),  # این ماه قبلاً generate شده
        )

        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )

        from apps.expenses.models import Expense
        url = reverse('expenses:expense-list')

        client.get(url)
        client.get(url)

        assert Expense.objects.filter(
            user=user,
            description='[Recurring] Netflix'
        ).count() == 0


@pytest.mark.django_db
class TestBudgetAlerts:
    """
    Test budget alert system
    """

    def test_warning_alert_at_80_percent(self, db):
        user = UserFactory()
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
            amount=Decimal('80.00'),
            date=date(2026, 6, 1)
        )

        assert budget.alert_level == 'warning'
        assert budget.usage_percentage == 80.0

    def test_exceeded_alert_over_100_percent(self, db):
        user = UserFactory()
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
            date=date(2026, 6, 1)
        )

        assert budget.alert_level == 'exceeded'
        assert budget.remaining_amount == Decimal('-50.00')

    def test_no_alert_under_80_percent(self, db):
        user = UserFactory()
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
            amount=Decimal('50.00'),
            date=date(2026, 6, 1)
        )

        assert budget.alert_level == 'none'


@pytest.mark.django_db
class TestFinancialHealthScore:
    """
    Test financial health score
    """

    def test_excellent_score(self, db):
        user = UserFactory()

        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )

        source = IncomeSourceFactory(user=user)
        category = CategoryFactory(user=user)

        IncomeFactory(
            user=user, source=source,
            amount=Decimal('5000.00'),
            date=date(2026, 6, 1)
        )
        ExpenseFactory(
            user=user, category=category,
            amount=Decimal('1000.00'),
            date=date(2026, 6, 1)
        )

        url = reverse('analytics:health')
        response = client.get(url, {'months': 1})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['score'] >= 60
        assert response.data['savings_rate'] == 80.0

    def test_poor_score(self, db):
        user = UserFactory()

        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )

        source = IncomeSourceFactory(user=user)
        category = CategoryFactory(user=user)

        IncomeFactory(
            user=user, source=source,
            amount=Decimal('1000.00'),
            date=date(2026, 6, 1)
        )
        ExpenseFactory(
            user=user, category=category,
            amount=Decimal('950.00'),
            date=date(2026, 6, 1)
        )

        url = reverse('analytics:health')
        response = client.get(url, {'months': 1})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['score'] <= 40
        assert len(response.data['suggestions']) > 0