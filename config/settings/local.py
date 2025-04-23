import socket
from datetime import timedelta

from .base import *
from .base import env

DEBUG = True

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="36r_!xm+r$egega@)pgb*1&uv^wl56j5j0+cjs039z&n(gy523",
)
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]

# CACHES

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": env("REDIS_PASSWORD", default="redispassword"),
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "vulipay",
        "TIMEOUT": 60 * 60 * 24,  # 24 hours in seconds
    }
}

# Set up session cache
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# EMAIL

EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# AWS S3 and CloudFront settings
# For local development, you can enable these to test S3 integration
# Or leave them disabled to use local file storage
USE_S3_STORAGE = env.bool(
    "USE_S3_STORAGE", default=False
)  # Set to True to test S3 storage

# If enabling S3 storage locally, configure these with your credentials
if USE_S3_STORAGE:
    # Add django-storages to INSTALLED_APPS
    INSTALLED_APPS += ["storages"]

    # AWS credentials
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")

    # S3 settings
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")

    # CloudFront settings (if using)
    AWS_CLOUDFRONT_DOMAIN = env("AWS_CLOUDFRONT_DOMAIN", default=None)

    # For development, you might want to set this to False to avoid creating public files
    AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default="public-read")

# WhiteNoise

# INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS

# Try to get internal IPs, but don't fail if it doesn't work
try:
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]
except socket.gaierror:
    INTERNAL_IPS = ["127.0.0.1"]

# django-extensions

INSTALLED_APPS += ["django_extensions"]

SIMPLE_JWT = {
    **SIMPLE_JWT,
    "SIGNING_KEY": env(
        "JWT_SECRET_KEY", default="36r_!xm+r$egega@)pgb*1&uv^wl56j5j0+cjs039z&n(gy523"
    ),
    "ACCESS_TOKEN_LIFETIME": timedelta(days=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=10),
}
