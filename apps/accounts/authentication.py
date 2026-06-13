from datetime import datetime, timezone as dt_timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class BlacklistableJWTAuthentication(JWTAuthentication):
    """
    چک می‌کنه که access token در blacklist نباشه
    """
    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)

        from .models import BlacklistedAccessToken
        jti = validated_token.get('jti')
        if jti and BlacklistedAccessToken.is_blacklisted(jti):
            raise InvalidToken('Token has been blacklisted')

        return validated_token


class BlacklistableJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """
    به spectacular میگه که این custom class همون JWT Bearer هست
    """
    target_class = 'apps.accounts.authentication.BlacklistableJWTAuthentication'
    name = 'JWTAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }