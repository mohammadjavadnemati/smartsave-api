from django.contrib.auth import get_user_model
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers as drf_serializers
from datetime import datetime, timezone as dt_timezone
from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken




User = get_user_model()


@extend_schema(tags=['Auth'])
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # ساخت توکن بعد از ثبت‌نام
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Auth'])
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer







@extend_schema(
    tags=['Auth'],
    request=inline_serializer(
        name='LogoutRequest',
        fields={'refresh': drf_serializers.CharField()}
    ),
    responses={
        200: OpenApiResponse(description='Successfully logged out'),
        400: OpenApiResponse(description='Invalid token'),
    }
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .models import BlacklistedAccessToken
        import logging
        logger = logging.getLogger(__name__)

        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                raw_access_token = auth_header.split(' ')[1]
                access_token = AccessToken(raw_access_token)
                jti = access_token.get('jti')
                exp = access_token.get('exp')
                expires_at = datetime.fromtimestamp(exp, tz=dt_timezone.utc)

                BlacklistedAccessToken.objects.get_or_create(
                    jti=jti,
                    defaults={'expires_at': expires_at}
                )

            return Response(
                {'message': 'Successfully logged out'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            # خطای دقیق رو برگردون
            logger.error(f'Logout error: {type(e).__name__}: {e}')
            return Response(
                {'error': f'{type(e).__name__}: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

@extend_schema(tags=['Auth'])
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=['Auth'],
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(description='Password changed successfully'),
        400: OpenApiResponse(description='Validation error'),
    }
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )

# @extend_schema(tags=['Auth'])
# class ChangePasswordView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request):
#         serializer = ChangePasswordSerializer(
#             data=request.data,
#             context={'request': request}
#         )
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(
#             {'message': 'Password changed successfully'},
#             status=status.HTTP_200_OK
#         )