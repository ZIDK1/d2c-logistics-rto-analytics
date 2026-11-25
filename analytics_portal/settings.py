"""
Minimal Django configuration for D2C Logistics & RTO Analytics Portal.
Queries data/d2c_logistics.db directly via parameterized sqlite3 views.
"""

import os

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-dev-d2c-logistics-rto-portal-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "analytics_portal.urls"
TEMPLATES = []
WSGI_APPLICATION = "analytics_portal.wsgi.application"
DATABASES = {}
USE_TZ = True
