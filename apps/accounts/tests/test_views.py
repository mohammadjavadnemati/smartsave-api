import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from .factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


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
class TestRegister:

    def test_register_success(self, api_client):
        url = reverse('accounts:register')
        data = {
            'email': 'newuser@example.com',
            'first_name': 'Ali',
            'last_name': 'Mohammadi',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'tokens' in response.data
        assert response.data['user']['email'] == 'newuser@example.com'

    def test_register_password_mismatch(self, api_client):
        url = reverse('accounts:register')
        data = {
            'email': 'test@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'DifferentPass123!',
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, user):
        url = reverse('accounts:register')
        data = {
            'email': user.email,
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:

    def test_login_success(self, api_client, user):
        url = reverse('accounts:login')
        data = {'email': user.email, 'password': 'TestPass123!'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_wrong_password(self, api_client, user):
        url = reverse('accounts:login')
        data = {'email': user.email, 'password': 'WrongPass!'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProfile:

    def test_get_profile(self, auth_client):
        client, user = auth_client
        url = reverse('accounts:profile')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_update_profile(self, auth_client):
        client, user = auth_client
        url = reverse('accounts:profile')
        data = {'first_name': 'Reza', 'last_name': 'Ahmadi'}
        response = client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Reza'

    def test_profile_unauthenticated(self, api_client):
        url = reverse('accounts:profile')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestLogout:

    def test_logout_success(self, auth_client):
        client, user = auth_client
        refresh = RefreshToken.for_user(user)
        url = reverse('accounts:logout')
        response = client.post(url, {'refresh': str(refresh)})
        assert response.status_code == status.HTTP_200_OK

    def test_logout_invalid_token(self, auth_client):
        client, _ = auth_client
        url = reverse('accounts:logout')
        response = client.post(url, {'refresh': 'invalid-token'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST