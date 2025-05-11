from pathlib import Path

import environ

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

APPS_DIR = ROOT_DIR / "app"

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    env.read_env(str(ROOT_DIR / ".env"))

# GENERAL

DEBUG = env.bool("DJANGO_DEBUG", False)
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [str(ROOT_DIR / "locale")]

# DATABASES

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

# APPS

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.forms",
]

THIRD_PARTY_APPS = [
    "phonenumber_field",
    "rest_framework_simplejwt",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
]

LOCAL_APPS = [
    "app.accounts",
    "app.transactions",
    "app.verify.apps.VerifyConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Add django-storages to INSTALLED_APPS if USE_S3_STORAGE is enabled
if env.bool("USE_S3_STORAGE", default=False):
    INSTALLED_APPS += ["storages"]

# OTP Settings
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 3
# Progressive waiting periods in seconds: 0s, 5s, 30s, 5min, 30min, 1h
OTP_WAITING_PERIODS = [0, 5, 30, 300, 1800, 3600]

# AUTHENTICATION

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# PASSWORDS

PASSWORD_HASHERS = [
    # "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# MEDIA

MEDIA_ROOT = str(APPS_DIR / "media")
MEDIA_URL = "/media/"

# AWS S3 and CloudFront settings
# In production, these should all come from environment variables
USE_S3_STORAGE = env.bool("USE_S3_STORAGE", default=False)

if USE_S3_STORAGE:
    # AWS credentials
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")

    # S3 settings
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
    AWS_S3_CUSTOM_DOMAIN = env("AWS_CLOUDFRONT_DOMAIN", default=None)
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",  # 1 day cache
    }
    AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default="public-read")
    AWS_LOCATION = "media"

    # Only use MediaRootS3BotoStorage for profile pictures to avoid disrupting other code
    MEDIA_URL = (
        f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/"
        if AWS_S3_CUSTOM_DOMAIN
        else f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{AWS_LOCATION}/"
    )

    # AWS CloudFront settings
    AWS_CLOUDFRONT_DOMAIN = env("AWS_CLOUDFRONT_DOMAIN", default=None)
    if AWS_CLOUDFRONT_DOMAIN:
        MEDIA_URL = f"https://{AWS_CLOUDFRONT_DOMAIN}/{AWS_LOCATION}/"

STATIC_ROOT = str(ROOT_DIR / "staticfiles")
STATIC_URL = "/static/"
STATICFILES_DIRS = [str(APPS_DIR / "static")]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# TEMPLATES

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(APPS_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# SECURITY

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# CORS settings
CORS_ALLOW_ALL_ORIGINS = False  # Don't allow all origins by default

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Encryption key for user data encryption
# In production, this should be set as an environment variable
ENCRYPTION_KEY = env(
    "ENCRYPTION_KEY", default="Fn0oZPGHKl7D2cSV1Ysq-T9yeuO9tKGXxTOdLG2Bw-g="
)

# EMAIL

EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_TIMEOUT = 5

# ADMIN

ADMIN_URL = "admin/"

ADMINS = [("""Aymar Amono""", "aymar.amono@vulipay.com")]

MANAGERS = ADMINS

# LOGGING

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# DJANGO REST FRAMEWORK

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "app.accounts.authentication.AppJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "account_id",
}

OTP_LENGTH = 6
DIAL_OUT_CODE = "+"
OTP_TIMESTAMP = 30
PAYMENT_CODE_PREFFIX = "vulipay"
PIN_MAX_LENGTH = 4
MASTER_INTL_PHONE_NUMBER = "0000000000"
MASTER_PHONE_NUMBER = "00000000"

# SWAGGER SETTINGS
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
    "USE_SESSION_AUTH": False,
}

# DRF Spectacular Settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Vulipay API",
    "DESCRIPTION": "API documentation for Vulipay",
    "VERSION": "v1",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {
        "name": "Vulipay",
        "email": "contact@vulipay.com",
    },
    "LICENSE": {
        "name": "Proprietary License",
    },
    "TERMS_OF_SERVICE": "https://www.vulipay.com/terms/",
}

# Twilio Configuration (for SMS OTP)
TWILIO_ENABLED = env.bool("TWILIO_ENABLED", default=False)
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_PHONE_NUMBER = env("TWILIO_PHONE_NUMBER", default="")
