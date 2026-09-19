import dj_database_url
from decouple import config
from .base import *

DEBUG = False

ALLOWED_HOSTS = [h for h in config('ALLOWED_HOSTS', default='').split(',') if h]
render_host = config('RENDER_EXTERNAL_HOSTNAME', default='')
if render_host:
    ALLOWED_HOSTS.append(render_host)

DATABASES = {
    'default': dj_database_url.parse(config('DATABASE_URL'), conn_max_age=600)
}

# WhiteNoise باید بعد از CorsMiddleware و قبل از بقیه بیاید
MIDDLEWARE.insert(2, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [o for o in config('CSRF_TRUSTED_ORIGINS', default='').split(',') if o]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [o for o in config('CORS_ALLOWED_ORIGINS', default='').split(',') if o]