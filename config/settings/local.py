import socket

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
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# EMAIL

EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# WhiteNoise

# INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS

hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

# django-extensions

INSTALLED_APPS += ["django_extensions"]

# Project related config
INSTALLED_APPS += [
    "users.apps.UsersConfig",
    "otp_auth.apps.OtpAuthConfig",
    "countries.apps.CountriesConfig",
]
